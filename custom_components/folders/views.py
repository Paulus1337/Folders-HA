from __future__ import annotations

from collections.abc import Callable
from contextlib import suppress
from datetime import timedelta
from http import HTTPStatus
from operator import itemgetter
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

from .api import FOLDER_PAGES, Folder, FoldersError, Offer, Shop, async_get_image, normalize, unique
from .const import (
    DOMAIN,
    HIT_LIMIT,
    MAX_BOX,
    MENTION_LIMIT,
    NEAREST_LIMIT,
    OFFER_LIMIT,
    OVERVIEW_DEALS,
    SCOPES,
    SEARCH_LIMIT,
    STORE_IDS,
    SUGGEST_STORES,
    SUGGEST_TITLES,
    WORD_MENTIONS,
)
from .coordinator import FoldersCoordinator, FoldersData
from .entity import match_attributes, nearby, offer_attributes, period
from .watch import clean

IMAGE_LIMIT = 2 * 1024 * 1024
PAGE_LIMIT = 4 * 1024 * 1024
CACHE_SECONDS = 6 * 3600
CACHE_ITEMS = 200
CACHE_BYTES = 20 * 1024 * 1024
SIGNED_FOR = timedelta(hours=1)
NEW_FOR = timedelta(days=3)
INVALID_TEXT = "Use 2 to 40 characters"
_UUID = re.compile(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}")
_PAGE_KEY = re.compile(rf"({_UUID.pattern})\.([1-9][0-9]{{0,2}})")
UUID = vol.All(str, vol.Lower, vol.Match(rf"{_UUID.pattern}\Z"))
STORES = vol.All([UUID], vol.Length(min=1, max=STORE_IDS))
_KM = itemgetter(1)

type Signer = Callable[[str, str], str] | None


def loaded_coordinator(hass: HomeAssistant) -> FoldersCoordinator | None:
    entries = hass.config_entries.async_loaded_entries(DOMAIN)
    return entries[0].runtime_data if entries else None


def search_text(value: Any) -> str:
    if (text := clean(cv.string(value))) is None:
        raise vol.Invalid(INVALID_TEXT)
    return text


def _signer(hass: HomeAssistant, connection: websocket_api.ActiveConnection) -> Callable[[str, str], str]:
    def sign(kind: str, key: str) -> str:
        path = f"/api/{DOMAIN}/image/{kind}/{key}"
        return async_sign_path(hass, path, SIGNED_FOR, refresh_token_id=connection.refresh_token_id)

    return sign


def _image(sign: Signer, offer: Offer) -> dict[str, Any]:
    return {} if sign is None else {"image": sign("offer", offer.offer_id) if offer.image else None}


def _thumb(sign: Callable[[str, str], str], folder: Folder, number: int) -> str | None:
    return sign("thumb", f"{folder.folder_id}.{number}") if folder.page(number, "-thumb") else None


def offer_row(data: FoldersData, offer: Offer, sign: Signer = None) -> dict[str, Any]:
    return {**offer_attributes(data, offer), "offer_id": offer.offer_id, **_image(sign, offer)}


def _result(
    coordinator: FoldersCoordinator, offer: Offer, sign: Signer, near: tuple[float, Shop] | None
) -> dict[str, Any]:
    data = coordinator.data
    return {
        "offer_id": offer.offer_id,
        "title": offer.title,
        "price": offer.price,
        "sale_price": offer.sale_price,
        "description": offer.description,
        "product_category": offer.product_category,
        **_image(sign, offer),
        "store_id": offer.store_id,
        "store": data.stores[offer.store_id].name,
        "folder_id": offer.folder_id,
        "folder": data.index[offer.folder_id].name or None,
        "page": offer.page,
        "valid_from": offer.valid_from.isoformat(),
        "valid_until": offer.valid_until.isoformat(),
        "upcoming": offer.valid_from > dt_util.utcnow(),
        "followed": offer.store_id in data.followed,
        **nearby(near),
    }


def _hit(data: FoldersData, folder: Folder, pages: tuple[int, ...], sign: Signer) -> dict[str, Any]:
    return {
        "folder_id": folder.folder_id,
        "store_id": folder.store_id,
        "store": data.stores[folder.store_id].name,
        "folder": folder.name or None,
        "pages": list(pages),
        "valid_from": folder.valid_from.isoformat(),
        "valid_until": folder.valid_until.isoformat(),
        "upcoming": folder.valid_from > dt_util.utcnow(),
        "followed": folder.store_id in data.followed,
        "url": folder.url,
        **({} if sign is None else {"thumb": _thumb(sign, folder, pages[0])}),
    }


async def async_search_answer(
    coordinator: FoldersCoordinator, text: str, scope: str, sign: Signer = None
) -> dict[str, Any]:
    coordinator.shops.async_start(dt_util.utcnow(), coordinator.data.stores.values())
    found = await coordinator.async_search(text)
    data, now, hass = coordinator.data, dt_util.utcnow(), coordinator.hass

    def in_scope(store_id: str) -> bool:
        return store_id in data.stores and (scope == "all" or store_id in data.followed)

    offers = unique(
        offer
        for offer in found.offers
        if offer.valid_until > now and offer.folder_id in data.index and in_scope(offer.store_id)
    )
    chosen = sorted(offers, key=lambda offer: (offer.valid_from > now, offer.store_id not in data.followed))
    chosen = sorted(
        chosen[:SEARCH_LIMIT],
        key=lambda offer: (
            offer.store_id not in data.followed,
            data.stores[offer.store_id].name.casefold(),
            offer.title.casefold(),
            offer.valid_from > now,
        ),
    )
    near = coordinator.shops.nearest({offer.store_id for offer in chosen}, hass.config.latitude, hass.config.longitude)
    hits = [
        (data.index[folder_id], pages)
        for folder_id, pages in (found.folders or {}).items()
        if folder_id in data.index and in_scope(data.index[folder_id].store_id)
    ]
    hits.sort(
        key=lambda hit: (
            hit[0].store_id not in data.followed,
            data.stores[hit[0].store_id].name.casefold(),
            hit[0].name.casefold(),
        )
    )
    answer = {
        "results": [_result(coordinator, offer, sign, near.get(offer.store_id)) for offer in chosen],
        "more": found.more or len(offers) > SEARCH_LIMIT,
        "folders": [_hit(data, folder, pages, sign) for folder, pages in hits[:HIT_LIMIT]],
    }
    if sign is None:
        return answer
    coordinator.client.keep(chosen)
    stores = [data.stores[store_id] for store_id in found.stores if store_id in data.folders and in_scope(store_id)]
    stores.sort(key=lambda store: (store.store_id not in data.followed, store.name.casefold()))
    answer["stores"] = [
        {
            "id": store.store_id,
            "name": store.name,
            "followed": store.store_id in data.followed,
            "folder_id": data.folders[store.store_id][0].folder_id,
            "logo": sign("logo", store.store_id) if store.logo else None,
        }
        for store in stores[:HIT_LIMIT]
    ]
    return answer


def _box(msg: dict[str, Any]) -> dict[str, Any]:
    if msg["south"] >= msg["north"] or msg["west"] >= msg["east"]:
        raise vol.Invalid("south must be below north and west must be left of east")
    return msg


def _shop(shop: Shop) -> dict[str, Any]:
    return {
        "id": shop.shop_id,
        "lat": shop.latitude,
        "lon": shop.longitude,
        "store": shop.store_id,
        "address": shop.address,
        "hours": shop.hours or None,
    }


def _stores(data: FoldersData, shops: list[Shop], sign: Callable[[str, str], str]) -> dict[str, Any]:
    stores: dict[str, Any] = {}
    for store_id in dict.fromkeys(shop.store_id for shop in shops):
        store, folder = data.stores[store_id], data.folders[store_id][0]
        stores[store_id] = {
            "name": store.name,
            "url": store.url,
            "logo": sign("logo", store_id) if store.logo else None,
            "categories": list(store.categories),
            "followed": store_id in data.followed,
            "folder": {
                "id": folder.folder_id,
                "name": folder.name or None,
                **period(folder),
                "cover": sign("cover", folder.folder_id) if folder.cover else None,
            },
        }
    return stores


def _shop_list(hass: HomeAssistant, answer: dict[str, Any]) -> tuple[FoldersCoordinator | None, dict[str, Any]]:
    if (coordinator := loaded_coordinator(hass)) is None:
        return None, {**answer, "status": "not_loaded"}
    shops = coordinator.shops
    shops.async_start(dt_util.utcnow(), coordinator.data.stores.values())
    if shops.updated is None:
        return None, {**answer, "status": "loading" if shops.loading else "unavailable"}
    return coordinator, answer


@websocket_api.websocket_command(
    vol.All(
        vol.Schema(
            {
                vol.Required("type"): f"{DOMAIN}/shops",
                vol.Required("south"): cv.latitude,
                vol.Required("west"): cv.longitude,
                vol.Required("north"): cv.latitude,
                vol.Required("east"): cv.longitude,
                vol.Optional("stores"): STORES,
            }
        ),
        _box,
    )
)
@callback
def websocket_shops(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    coordinator, answer = _shop_list(hass, {"status": "ok", "shops": [], "stores": {}, "more": False})
    if coordinator is not None:
        south, west, north, east = msg["south"], msg["west"], msg["north"], msg["east"]
        if north - south > MAX_BOX or east - west > MAX_BOX:
            answer = {**answer, "status": "zoom"}
        else:
            data = coordinator.data
            allowed = data.folders.keys() & set(msg["stores"]) if "stores" in msg else data.folders
            found, more = coordinator.shops.find(south, west, north, east, allowed)
            stores = _stores(data, found, _signer(hass, connection))
            answer = {**answer, "shops": [_shop(shop) for shop in found], "stores": stores, "more": more}
    connection.send_result(msg["id"], answer)


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/nearest",
        vol.Required("stores"): STORES,
        vol.Inclusive("latitude", "point"): cv.latitude,
        vol.Inclusive("longitude", "point"): cv.longitude,
        vol.Optional("limit", default=10): vol.All(vol.Coerce(int), vol.Range(min=1, max=NEAREST_LIMIT)),
    }
)
@callback
def websocket_nearest(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    coordinator, answer = _shop_list(hass, {"status": "ok", "shops": [], "stores": {}})
    if coordinator is not None:
        data = coordinator.data
        latitude, longitude = msg.get("latitude", hass.config.latitude), msg.get("longitude", hass.config.longitude)
        stores = [store_id for store_id in dict.fromkeys(msg["stores"]) if store_id in data.folders]
        found = coordinator.shops.nearby(stores, latitude, longitude, msg["limit"])
        shops = [{**_shop(shop), "distance": round(km, 1)} for km, shop in found]
        answer = {
            **answer,
            "shops": shops,
            "stores": _stores(data, [shop for _, shop in found], _signer(hass, connection)),
        }
    connection.send_result(msg["id"], answer)


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/area",
        vol.Inclusive("latitude", "point"): cv.latitude,
        vol.Inclusive("longitude", "point"): cv.longitude,
        vol.Optional("radius", default=5.0): vol.All(vol.Coerce(float), vol.Range(min=0.5, max=50)),
    }
)
@callback
def websocket_area(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    coordinator, answer = _shop_list(hass, {"status": "ok", "stores": {}})
    if coordinator is not None:
        latitude, longitude = msg.get("latitude", hass.config.latitude), msg.get("longitude", hass.config.longitude)
        found = coordinator.shops.around(coordinator.data.folders, latitude, longitude, msg["radius"])
        answer = {**answer, "stores": {store_id: round(km, 1) for store_id, km in sorted(found.items(), key=_KM)}}
    connection.send_result(msg["id"], answer)


@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/overview", vol.Optional("theme"): vol.All(str, vol.Match(r"[a-z0-9-]{1,120}\Z"))}
)
@websocket_api.async_response
async def websocket_overview(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    connection.send_result(msg["id"], await _async_overview(hass, connection, msg.get("theme")))


async def _async_overview(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, theme: str | None
) -> dict[str, Any]:
    if (coordinator := loaded_coordinator(hass)) is None:
        empty: dict[str, Any] = {key: [] for key in ("categories", "themes", "stores", "folders", "deals")}
        return {"status": "not_loaded", **empty, "watch": {"words": [], "matches": [], "mentions": []}}
    try:
        deals = await coordinator.async_deals(theme)
    except FoldersError:
        deals = coordinator.data.deals
    data, now, sign = coordinator.data, dt_util.utcnow(), _signer(hass, connection)
    chosen = [folder for store_id in data.followed for folder in data.folders.get(store_id, [])]
    folders = sorted(chosen, key=lambda folder: (data.stores[folder.store_id].name.casefold(), folder.store_id))
    deals, matches = deals[:OVERVIEW_DEALS], data.offers[:OFFER_LIMIT]
    mentions = [(word, *hit) for word, hits in data.mentions.items() for hit in hits[:WORD_MENTIONS]][:MENTION_LIMIT]
    coordinator.client.keep([*deals, *matches])
    used = dict.fromkeys(item.store_id for item in (*folders, *deals, *matches, *(folder for _, folder, _ in mentions)))
    return {
        "status": "ok",
        "categories": [
            {"slug": category.slug, "name": category.name}
            for category in sorted(data.categories.values(), key=lambda category: category.name.casefold())
        ],
        "themes": [
            {"slug": label.slug, "name": label.name}
            for label in data.themes.values()
            if any(label.slug in folder.themes and folder.valid_from <= now for folder in folders)
        ],
        "stores": [
            {
                "id": store.store_id,
                "name": store.name,
                "categories": list(store.categories),
                "logo": sign("logo", store.store_id) if store.logo else None,
                "followed": store.store_id in data.followed,
            }
            for store in (data.stores[store_id] for store_id in used)
        ],
        "folders": [
            {
                "id": folder.folder_id,
                "store_id": folder.store_id,
                "name": folder.name or None,
                "valid_from": folder.valid_from.isoformat(),
                "valid_until": folder.valid_until.isoformat(),
                "upcoming": folder.valid_from > now,
                "new": folder.created is not None and now - folder.created < NEW_FOR,
                "featured": folder.folder_id in data.featured,
                "themes": list(folder.themes),
                "cover": sign("cover", folder.folder_id) if folder.cover else None,
                "url": folder.url,
            }
            for folder in folders
        ],
        "deals": [offer_row(data, offer, sign) for offer in deals],
        "watch": {
            "words": coordinator.watch.words,
            "matches": [
                {
                    **offer_row(data, offer, sign),
                    "description": offer.description,
                    "word": offer.word,
                    **match_attributes(data, offer),
                }
                for offer in matches
            ],
            "mentions": [
                {
                    "word": word,
                    "store_id": folder.store_id,
                    "store": data.stores[folder.store_id].name,
                    "folder_id": folder.folder_id,
                    "folder": folder.name or None,
                    "pages": list(pages),
                    "valid_from": folder.valid_from.isoformat(),
                    "valid_until": folder.valid_until.isoformat(),
                    "thumb": _thumb(sign, folder, pages[0]),
                }
                for word, folder, pages in mentions
            ],
        },
    }


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/pages", vol.Required("folder_id"): UUID})
@websocket_api.async_response
async def websocket_pages(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    connection.send_result(msg["id"], await _async_pages(hass, connection, msg["folder_id"]))


async def _async_pages(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, folder_id: str
) -> dict[str, Any]:
    answer: dict[str, Any] = {"status": "ok", "folder": None, "pages": [], "thumbs": [], "offers": []}
    if (coordinator := loaded_coordinator(hass)) is None:
        return {**answer, "status": "not_loaded"}
    data = coordinator.data
    if (folder := data.index.get(folder_id)) is None:
        return {**answer, "status": "unknown"}
    answer["folder"] = {
        "id": folder.folder_id,
        "store_id": folder.store_id,
        "store": data.stores[folder.store_id].name,
        "name": folder.name or None,
        "valid_from": folder.valid_from.isoformat(),
        "valid_until": folder.valid_until.isoformat(),
        "upcoming": folder.valid_from > dt_util.utcnow(),
        "url": folder.url,
        "website": data.stores[folder.store_id].website,
        "themes": list(folder.themes),
    }
    if folder.page(1) is None:
        return {**answer, "status": "unavailable"}
    try:
        count, offers = await coordinator.async_folder(folder)
    except FoldersError:
        return {**answer, "status": "unavailable"}
    sign = _signer(hass, connection)
    shown = sorted(
        unique(offer for offer in offers if offer.page and offer.page <= count), key=lambda offer: offer.page
    )
    coordinator.client.keep(shown)
    numbers = range(1, count + 1)
    return {
        **answer,
        "pages": [sign("page", f"{folder_id}.{number}") for number in numbers],
        "thumbs": [sign("thumb", f"{folder_id}.{number}") for number in numbers],
        "offers": [
            {
                "offer_id": offer.offer_id,
                "title": offer.title,
                "price": offer.price,
                "sale_price": offer.sale_price,
                "description": offer.description,
                "product_category": offer.product_category,
                "page": offer.page,
                **_image(sign, offer),
            }
            for offer in shown
        ],
    }


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/search",
        vol.Required("query"): cv.string,
        vol.Optional("scope", default=SCOPES[0]): vol.In(SCOPES),
    }
)
@websocket_api.async_response
async def websocket_search(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    if (text := clean(msg["query"])) is None:
        connection.send_error(msg["id"], websocket_api.ERR_INVALID_FORMAT, INVALID_TEXT)
        return
    answer: dict[str, Any] = {"status": "ok", "results": [], "more": False, "folders": [], "stores": []}
    if (coordinator := loaded_coordinator(hass)) is None:
        answer["status"] = "not_loaded"
    else:
        try:
            answer.update(await async_search_answer(coordinator, text, msg["scope"], _signer(hass, connection)))
        except FoldersError:
            answer["status"] = "unavailable"
    connection.send_result(msg["id"], answer)


def _suggested_products(data: FoldersData, found: list[tuple[str, str]]) -> list[dict[str, str]]:
    now = dt_util.utcnow()
    titles: dict[str, str] = {}
    for title, folder_id in found:
        if folder_id in data.index and data.index[folder_id].valid_until > now:
            titles.setdefault(normalize(title), title)
    return [{"title": title} for title in list(titles.values())[:SUGGEST_TITLES]]


def _suggested_stores(data: FoldersData, key: str, sign: Callable[[str, str], str]) -> list[dict[str, Any]]:
    stores = [data.stores[store_id] for store_id in data.folders if key in normalize(data.stores[store_id].name)]
    stores.sort(key=lambda store: (not normalize(store.name).startswith(key), store.name.casefold()))
    return [
        {
            "id": store.store_id,
            "name": store.name,
            "logo": sign("logo", store.store_id) if store.logo else None,
            "folder_id": data.folders[store.store_id][0].folder_id,
        }
        for store in stores[:SUGGEST_STORES]
    ]


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/suggest", vol.Required("query"): cv.string})
@websocket_api.async_response
async def websocket_suggest(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    if (text := clean(msg["query"])) is None:
        connection.send_error(msg["id"], websocket_api.ERR_INVALID_FORMAT, INVALID_TEXT)
        return
    answer: dict[str, Any] = {"status": "ok", "products": [], "stores": []}
    if (coordinator := loaded_coordinator(hass)) is None:
        answer["status"] = "not_loaded"
    elif key := normalize(text):
        with suppress(FoldersError):
            found = await coordinator.async_suggest(text)
            answer["products"] = _suggested_products(coordinator.data, found)
        answer["stores"] = _suggested_stores(coordinator.data, key, _signer(hass, connection))
    connection.send_result(msg["id"], answer)


@websocket_api.websocket_command(
    {vol.Required("type"): f"{DOMAIN}/find", vol.Required("folder_id"): UUID, vol.Required("query"): cv.string}
)
@websocket_api.async_response
async def websocket_find(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    if (text := clean(msg["query"])) is None:
        connection.send_error(msg["id"], websocket_api.ERR_INVALID_FORMAT, INVALID_TEXT)
        return
    answer: dict[str, Any] = {"status": "ok", "pages": []}
    if (coordinator := loaded_coordinator(hass)) is None:
        answer["status"] = "not_loaded"
    elif (folder := coordinator.data.index.get(msg["folder_id"])) is None:
        answer["status"] = "unknown"
    else:
        try:
            pages = None if folder.slug is None else await coordinator.async_find(folder, text)
        except FoldersError:
            pages = None
        if pages is None:
            answer["status"] = "unavailable"
        else:
            answer["pages"] = pages
    connection.send_result(msg["id"], answer)


def _source(coordinator: FoldersCoordinator | None, kind: str, key: str) -> str | None:
    if coordinator is None:
        return None
    data = coordinator.data
    if kind == "offer":
        return coordinator.client.images.get(key)
    if kind in ("page", "thumb"):
        if not (found := _PAGE_KEY.fullmatch(key)) or (folder := data.index.get(found[1])) is None:
            return None
        number, count = int(found[2]), coordinator.page_count(folder.folder_id)
        if kind == "page":
            return folder.page(number) if number <= (count or 0) else None
        return folder.page(number, "-thumb") if number <= (count or FOLDER_PAGES) else None
    if not _UUID.fullmatch(key):
        return None
    if kind == "logo":
        return store.logo if (store := data.stores.get(key)) else None
    if kind == "cover":
        return folder.cover if (folder := data.index.get(key)) else None
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
        if (url := _source(loaded_coordinator(hass), kind, key)) is None:
            image = None
        elif kind == "page":
            image = await async_get_image(async_get_clientsession(hass), url, PAGE_LIMIT)
        else:
            image = await self._async_image(hass, url)
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
