from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Container, Iterable, Mapping
from contextlib import suppress
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from functools import partial
from operator import attrgetter
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import Category, Folder, FoldersClient, FoldersError, Found, Offer, Store, plain, unique
from .const import (
    CONF_ALWAYS_STORES,
    CONF_EXCLUDED_CATEGORIES,
    CONF_EXCLUDED_STORES,
    CONF_EXCLUDED_THEMES,
    CONF_WATCH_ALL,
    DOMAIN,
    LOGGER,
    OTHER,
)
from .shops import ShopList
from .watch import WatchList

type FoldersConfigEntry = ConfigEntry[FoldersCoordinator]
type Catalog = tuple[dict[str, Store], dict[str, Category], dict[str, Category]]
type Hit = tuple[Folder, tuple[int, ...]]

UPDATE_INTERVAL = timedelta(hours=3)
RETRY_INTERVAL = timedelta(minutes=15)
STORES_INTERVAL = timedelta(days=1)
WATCH_DELAY = 5
FOLDER_TIME = timedelta(hours=6)
SEARCH_TIME = timedelta(minutes=10)
LIVE_ITEMS = 100
TEXT_ITEMS = 20
CATEGORY_DEALS = 30
ALL_DEALS = 50
STORE_DEALS = 10
THEME_DEALS = 50
DEAL_STORES = 10
FOUND_PAGES = 50
_START = attrgetter("valid_from")
_RATIO = attrgetter("ratio")


def _shown(folders: list[Folder], now: datetime) -> list[Folder]:
    current = [folder for folder in folders if folder.valid_from <= now]
    first = max(current, key=_START) if current else min(folders, key=_START)
    return [first, *sorted((folder for folder in folders if folder is not first), key=_START)]


def _left_out(excluded: Container[str], store: Store) -> bool:
    return all(slug in excluded for slug in store.categories or (OTHER,))


def followed_stores(options: Mapping[str, Any], stores: Mapping[str, Store]) -> frozenset[str]:
    categories, excluded, always = (
        set(options.get(key, [])) for key in (CONF_EXCLUDED_CATEGORIES, CONF_EXCLUDED_STORES, CONF_ALWAYS_STORES)
    )
    return frozenset(
        store_id
        for store_id, store in stores.items()
        if store_id not in excluded and (store_id in always or not _left_out(categories, store))
    )


def current_offers(
    offers: Iterable[Offer], index: Container[str], stores: Container[str], now: datetime
) -> list[Offer]:
    return unique(
        offer
        for offer in offers
        if offer.store_id in stores and offer.folder_id in index and offer.valid_from <= now < offer.valid_until
    )


def _mentions(
    offered: Container[str],
    folders: Mapping[str, tuple[int, ...]],
    index: Mapping[str, Folder],
    watched: Container[str],
    stores: Mapping[str, Store],
) -> list[Hit]:
    hits = [
        (index[folder_id], pages)
        for folder_id, pages in folders.items()
        if folder_id in index and folder_id not in offered and index[folder_id].store_id in watched
    ]
    hits.sort(key=lambda hit: (stores[hit[0].store_id].name.casefold(), hit[0].name.casefold()))
    return hits


@dataclass(frozen=True, slots=True)
class FoldersData:
    stores: dict[str, Store]
    categories: dict[str, Category]
    themes: dict[str, Category]
    folders: dict[str, list[Folder]]
    index: dict[str, Folder]
    followed: frozenset[str]
    featured: frozenset[str]
    words: tuple[str, ...]
    matches: dict[str, list[Offer]]
    offered: dict[str, frozenset[str]]
    offers: list[Offer]
    best: dict[str, Offer | None]
    mentions: dict[str, list[Hit]]
    deals: list[Offer]


class FoldersCoordinator(DataUpdateCoordinator[FoldersData]):
    config_entry: FoldersConfigEntry

    def __init__(self, hass: HomeAssistant, entry: FoldersConfigEntry) -> None:
        super().__init__(hass, LOGGER, config_entry=entry, name=DOMAIN, update_interval=UPDATE_INTERVAL)
        self.client = FoldersClient(async_get_clientsession(hass))
        self.shops = ShopList(self)
        self.watch = WatchList(hass)
        self._catalog: tuple[datetime, Catalog] | None = None
        self._featured: frozenset[str] = frozenset()
        self._hits: dict[str, dict[str, tuple[int, ...]]] = {}
        self._folders: dict[str, tuple[datetime, Any]] = {}
        self._searches: dict[str, tuple[datetime, Any]] = {}
        self._texts: dict[str, tuple[datetime, Any]] = {}
        self._themes: dict[str, tuple[datetime, Any]] = {}
        self._live = asyncio.Semaphore(2)
        self._unsub_watch: CALLBACK_TYPE | None = None
        entry.async_on_unload(self._async_cancel_watch)

    @callback
    def _async_cancel_watch(self) -> None:
        if self._unsub_watch:
            self._unsub_watch()
            self._unsub_watch = None

    @callback
    def async_watch_changed(self) -> None:
        self._async_cancel_watch()
        self._unsub_watch = async_call_later(self.hass, WATCH_DELAY, self._async_watch_refresh)

    async def _async_watch_refresh(self, _: datetime) -> None:
        self._unsub_watch = None
        await self.async_refresh()

    async def _async_catalog(self) -> Catalog:
        stores = await self.client.async_get_stores()
        return stores, await self.client.async_get_categories(), await self.client.async_get_themes()

    def _deal_requests(self, catalog: Catalog, followed: frozenset[str]) -> list[dict[str, Any]]:
        stores, categories, _ = catalog
        options = self.config_entry.options
        excluded = set(options.get(CONF_EXCLUDED_CATEGORIES, []))
        always = [
            store_id
            for store_id in options.get(CONF_ALWAYS_STORES, [])
            if store_id in followed and _left_out(excluded, stores[store_id])
        ]
        return [
            *(
                {"limit": CATEGORY_DEALS, "affiliateCmsCategoryId": category.category_id}
                for slug, category in categories.items()
                if slug not in excluded
            ),
            *([{"limit": ALL_DEALS}] if OTHER not in excluded else []),
            *({"limit": STORE_DEALS, "retailerId": store_id} for store_id in always[:DEAL_STORES]),
        ]

    async def _async_update_data(self) -> FoldersData:
        now, words, options = dt_util.utcnow(), tuple(self.watch.words), self.config_entry.options
        try:
            if self._catalog is None or now - self._catalog[0] >= STORES_INTERVAL:
                self._catalog = (now, await self._async_catalog())
            stores, categories, themes = catalog = self._catalog[1]
            followed = followed_stores(options, stores)
            folders = await self.client.async_get_folders()
            with suppress(FoldersError):
                self._featured = await self.client.async_get_featured()
            found = {word: await self.client.async_search(word) for word in words}
            deals = [
                offer
                for request in self._deal_requests(catalog, followed)
                for offer in await self.client.async_get_deals(**request)
            ]
        except FoldersError as err:
            self.update_interval = RETRY_INTERVAL
            raise UpdateFailed(
                translation_domain=DOMAIN, translation_key="update_failed", translation_placeholders={"error": str(err)}
            ) from err
        self.update_interval = UPDATE_INTERVAL
        hidden = set(options.get(CONF_EXCLUDED_THEMES, []))
        index = {
            folder.folder_id: folder
            for folder in folders
            if folder.store_id in stores and folder.valid_until > now and hidden.isdisjoint(folder.themes)
        }
        grouped: dict[str, list[Folder]] = {}
        for folder in index.values():
            grouped.setdefault(folder.store_id, []).append(folder)
        watched = stores if options.get(CONF_WATCH_ALL) else followed
        matches = {word: current_offers(result.offers, index, watched, now) for word, result in found.items()}
        offered = {word: frozenset(offer.folder_id for offer in result.offers) for word, result in found.items()}
        offers = unique(replace(offer, word=word) for word, items in matches.items() for offer in items)
        self._hits = {
            word: self._hits[word] if result.folders is None else result.folders
            for word, result in found.items()
            if result.folders is not None or word in self._hits
        }
        return FoldersData(
            stores,
            categories,
            themes,
            {store_id: _shown(items, now) for store_id, items in grouped.items()},
            index,
            followed,
            self._featured.intersection(index),
            words,
            matches,
            offered,
            sorted(offers, key=lambda offer: (stores[offer.store_id].name.casefold(), offer.title.casefold())),
            {word: min(items, key=_RATIO, default=None) for word, items in matches.items()},
            {word: _mentions(offered[word], hits, index, watched, stores) for word, hits in self._hits.items()},
            sorted(current_offers(deals, index, followed, now), key=_RATIO),
        )

    async def _async_live[T](
        self,
        cache: dict[str, tuple[datetime, Any]],
        key: str,
        age: timedelta,
        fetch: Callable[[], Awaitable[T]],
        size: int = LIVE_ITEMS,
    ) -> T:
        if (cached := cache.get(key)) is None or dt_util.utcnow() - cached[0] >= age:
            async with self._live:
                cached = (dt_util.utcnow(), await fetch())
            cache.pop(key, None)
            cache[key] = cached
            while len(cache) > size:
                del cache[next(iter(cache))]
        return cached[1]

    async def async_search(self, text: str) -> Found:
        return await self._async_live(self._searches, text, SEARCH_TIME, partial(self.client.async_search, text))

    async def async_folder(self, folder: Folder) -> tuple[int, list[Offer]]:
        return await self._async_live(
            self._folders, folder.folder_id, FOLDER_TIME, partial(self.client.async_get_folder, folder)
        )

    async def async_find(self, folder: Folder, text: str) -> list[int] | None:
        async def fetch() -> tuple[str, ...]:
            texts = await self.client.async_get_text(folder)
            return await self.hass.async_add_executor_job(lambda: tuple(map(plain, texts)))

        pages = await self._async_live(self._texts, folder.folder_id, FOLDER_TIME, fetch, TEXT_ITEMS)
        if not pages:
            return None
        query = plain(text)
        return [number for number, page in enumerate(pages, 1) if query and query in page][:FOUND_PAGES]

    async def async_deals(self, theme: str | None) -> list[Offer]:
        if theme is None or (label := self.data.themes.get(theme)) is None:
            return self.data.deals
        offers = await self._async_live(
            self._themes,
            theme,
            SEARCH_TIME,
            partial(self.client.async_get_deals, THEME_DEALS, themeId=label.category_id),
        )
        data = self.data
        return sorted(current_offers(offers, data.index, data.followed, dt_util.utcnow()), key=_RATIO)

    def page_count(self, folder_id: str) -> int | None:
        return cached[1][0] if (cached := self._folders.get(folder_id)) else None
