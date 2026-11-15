from __future__ import annotations

import asyncio
from collections.abc import Container, Iterable
from dataclasses import astuple
from datetime import datetime, timedelta
import heapq
import math
from operator import itemgetter
from typing import TYPE_CHECKING, Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import storage
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util

from .api import FoldersError, Shop, Store, async_get_shops, parse_shops, parse_time
from .const import DOMAIN, LOGGER, MAX_SHOPS

if TYPE_CHECKING:
    from .coordinator import FoldersCoordinator

REFRESH = timedelta(days=14)
RETRY = timedelta(hours=1)
VERSION = 2
EARTH = 6371.0
_ROW = (str, float, float, str, str, str, str, str)
_FIRST = itemgetter(0)


def shop_storage(hass: HomeAssistant) -> storage.Store[dict[str, Any]]:
    return storage.Store(hass, 1, f"{DOMAIN}.shops")


def distance(latitude: float, longitude: float, shop: Shop) -> float:
    start, end = math.radians(latitude), math.radians(shop.latitude)
    half = math.sin((end - start) / 2) ** 2
    half += math.cos(start) * math.cos(end) * math.sin(math.radians(shop.longitude - longitude) / 2) ** 2
    return 2 * EARTH * math.asin(math.sqrt(half))


def _parse(body: bytes, stores: list[Store]) -> tuple[list[Shop], list[tuple[Any, ...]]]:
    shops = parse_shops(body, stores)
    return shops, [astuple(shop) for shop in shops]


def _shops(rows: list[Any], old: bool) -> list[Shop]:
    rows = [[*row, ""] if old and isinstance(row, list) else row for row in rows]
    return [
        Shop(*row)
        for row in rows
        if isinstance(row, list) and len(row) == len(_ROW) and all(map(isinstance, row, _ROW))
    ]


class ShopList:
    def __init__(self, coordinator: FoldersCoordinator) -> None:
        self._coordinator = coordinator
        self._storage = shop_storage(coordinator.hass)
        self._failed: datetime | None = None
        self._stale = False
        self._task: asyncio.Task[None] | None = None
        self._stores: dict[str, list[Shop]] = {}
        self.shops: list[Shop] = []
        self.updated: datetime | None = None

    @property
    def loading(self) -> bool:
        return self._task is not None and not self._task.done()

    def _use(self, shops: list[Shop], updated: datetime) -> None:
        self.shops, self.updated, self._stores = shops, updated, {}
        for shop in shops:
            self._stores.setdefault(shop.store_id, []).append(shop)

    async def async_load(self) -> None:
        stored = await self._storage.async_load()
        if (
            not isinstance(stored, dict)
            or (updated := parse_time(stored.get("time"))) is None
            or not isinstance(rows := stored.get("shops"), list)
        ):
            return
        self._stale = stored.get("version") != VERSION
        self._use(await self._coordinator.hass.async_add_executor_job(_shops, rows, self._stale), updated)

    @callback
    def async_start(self, now: datetime) -> None:
        fresh = not self._stale and self.updated is not None and timedelta(0) <= now - self.updated < REFRESH
        waiting = self._failed is not None and now - self._failed < RETRY
        if not (self.loading or fresh or waiting):
            coordinator = self._coordinator
            self._task = coordinator.config_entry.async_create_background_task(
                coordinator.hass, self._async_download(), f"{DOMAIN} shops"
            )

    async def _async_download(self) -> None:
        hass, stores = self._coordinator.hass, [*self._coordinator.data.stores.values()]
        try:
            body = await async_get_shops(async_get_clientsession(hass), stores)
            shops, rows = await hass.async_add_executor_job(_parse, body, stores)
        except FoldersError as err:
            self._failed = dt_util.utcnow()
            LOGGER.warning("Could not load the shops from OpenStreetMap, the map tries again after an hour: %s", err)
            return
        self._use(shops, dt_util.utcnow())
        self._failed, self._stale = None, False
        await self._storage.async_save({"version": VERSION, "time": self.updated.isoformat(), "shops": rows})

    def find(
        self, south: float, west: float, north: float, east: float, stores: Container[str]
    ) -> tuple[list[Shop], bool]:
        latitude, longitude = (south + north) / 2, (west + east) / 2
        scale = math.cos(math.radians(latitude)) ** 2
        found = [
            shop
            for shop in self.shops
            if south <= shop.latitude <= north and west <= shop.longitude <= east and shop.store_id in stores
        ]
        found.sort(key=lambda shop: (shop.latitude - latitude) ** 2 + (shop.longitude - longitude) ** 2 * scale)
        return found[:MAX_SHOPS], len(found) > MAX_SHOPS

    def nearest(self, stores: Iterable[str], latitude: float, longitude: float) -> dict[str, tuple[float, Shop]]:
        return {
            store_id: min(((distance(latitude, longitude, shop), shop) for shop in shops), key=_FIRST)
            for store_id in stores
            if (shops := self._stores.get(store_id))
        }

    def nearby(self, stores: Iterable[str], latitude: float, longitude: float, limit: int) -> list[tuple[float, Shop]]:
        found = (
            (distance(latitude, longitude, shop), shop)
            for store_id in stores
            for shop in self._stores.get(store_id, ())
        )
        return heapq.nsmallest(limit, found, key=_FIRST)
