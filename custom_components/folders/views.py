from __future__ import annotations

from datetime import timedelta
from http import HTTPStatus
import re
import time
from typing import Any

from aiohttp import hdrs, web
from homeassistant.components import websocket_api
from homeassistant.components.http import KEY_AUTHENTICATED, KEY_HASS, HomeAssistantView
from homeassistant.components.http.auth import async_sign_path
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util
import voluptuous as vol

from .api import async_get_image
from .const import DOMAIN, MAX_BOX
from .coordinator import FoldersCoordinator
from .entity import period

IMAGE_LIMIT = 2 * 1024 * 1024
CACHE_SECONDS = 6 * 3600
CACHE_ITEMS = 200
CACHE_BYTES = 20 * 1024 * 1024
SIGNED_FOR = timedelta(hours=1)
_UUID = re.compile(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", re.IGNORECASE)


def _coordinator(hass: HomeAssistant) -> FoldersCoordinator | None:
    entries = hass.config_entries.async_loaded_entries(DOMAIN)
    return entries[0].runtime_data if entries else None


def _box(msg: dict[str, Any]) -> dict[str, Any]:
    if msg["south"] >= msg["north"] or msg["west"] >= msg["east"]:
        raise vol.Invalid("south must be below north and west must be left of east")
    return msg


@websocket_api.websocket_command(
    vol.All(
        vol.Schema(
            {
                vol.Required("type"): f"{DOMAIN}/shops",
                vol.Required("south"): cv.latitude,
                vol.Required("west"): cv.longitude,
                vol.Required("north"): cv.latitude,
                vol.Required("east"): cv.longitude,
            }
        ),
        _box,
    )
)
@callback
def websocket_shops(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    connection.send_result(msg["id"], _answer(hass, connection, msg))


def _answer(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> dict[str, Any]:
    answer: dict[str, Any] = {"status": "ok", "shops": [], "stores": {}, "more": False}
    if (coordinator := _coordinator(hass)) is None:
        return {**answer, "status": "not_loaded"}
    shops, data = coordinator.shops, coordinator.data
    shops.async_start(dt_util.utcnow())
    south, west, north, east = msg["south"], msg["west"], msg["north"], msg["east"]
    if shops.updated is None:
        return {**answer, "status": "loading" if shops.loading else "unavailable"}
    if north - south > MAX_BOX or east - west > MAX_BOX:
        return {**answer, "status": "zoom"}

    def sign(kind: str, key: str) -> str:
        path = f"/api/{DOMAIN}/image/{kind}/{key}"
        return async_sign_path(hass, path, SIGNED_FOR, refresh_token_id=connection.refresh_token_id)

    found, more = shops.find(south, west, north, east, data.folders)
    stores: dict[str, Any] = {}
    for store_id in dict.fromkeys(shop.store_id for shop in found):
        store, folder = data.stores[store_id], data.folders[store_id][0]
        stores[store_id] = {
            "name": store.name,
            "url": store.url,
            "logo": sign("logo", store_id) if store.logo else None,
            "folder": {
                "name": folder.name or None,
                **period(folder),
                "cover": sign("cover", folder.folder_id) if folder.cover else None,
            },
        }
    shown = [
        {
            "id": shop.shop_id,
            "lat": shop.latitude,
            "lon": shop.longitude,
            "store": shop.store_id,
            "address": shop.address,
        }
        for shop in found
    ]
    return {**answer, "shops": shown, "stores": stores, "more": more}


def _source(coordinator: FoldersCoordinator | None, kind: str, key: str) -> str | None:
    if coordinator is None or not _UUID.fullmatch(key):
        return None
    data = coordinator.data
    if kind == "logo":
        return store.logo if (store := data.stores.get(key)) else None
    if kind == "cover":
        covers = (folder.cover for folders in data.folders.values() for folder in folders if folder.folder_id == key)
        return next(covers, None)
    return None


class FoldersImageView(HomeAssistantView):
    url = f"/api/{DOMAIN}/image/{{kind}}/{{key}}"
    name = f"api:{DOMAIN}:image"
    requires_auth = False

    def __init__(self) -> None:
        self._cache: dict[str, tuple[float, str, bytes]] = {}

    async def get(self, request: web.Request, kind: str, key: str) -> web.Response:
        if not request[KEY_AUTHENTICATED]:
            raise web.HTTPUnauthorized if hdrs.AUTHORIZATION in request.headers else web.HTTPForbidden
        hass = request.app[KEY_HASS]
        url = _source(_coordinator(hass), kind, key)
        image = await self._async_image(hass, url) if url else None
        if image is None:
            return web.Response(status=HTTPStatus.NOT_FOUND)
        return web.Response(body=image[1], content_type=image[0], headers={"Cache-Control": "private, max-age=3600"})

    async def _async_image(self, hass: HomeAssistant, url: str) -> tuple[str, bytes] | None:
        cache, now = self._cache, time.time()
        for old in [key for key, (added, *_) in cache.items() if now - added >= CACHE_SECONDS]:
            del cache[old]
        if (cached := cache.get(url)) is not None:
            return cached[1], cached[2]
        if (image := await async_get_image(async_get_clientsession(hass), url, IMAGE_LIMIT)) is None:
            return None
        cache.pop(url, None)
        cache[url] = (time.time(), *image)
        while len(cache) > CACHE_ITEMS or sum(len(item[2]) for item in cache.values()) > CACHE_BYTES:
            del cache[next(iter(cache))]
        return image
