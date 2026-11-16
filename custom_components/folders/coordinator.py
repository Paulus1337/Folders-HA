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

from .api import Category, Folder, FoldersClient, FoldersError, Found, Offer, QueryError, Shop, Store, plain, unique
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
from .watch import Watch, WatchList

type FoldersConfigEntry = ConfigEntry[FoldersCoordinator]
type Catalog = tuple[dict[str, Store], dict[str, Category], dict[str, Category]]
type Hit = tuple[Folder, tuple[int, ...]]
type Near = tuple[float, Shop]

UPDATE_INTERVAL = timedelta(hours=3)
RETRY_INTERVAL = timedelta(minutes=15)
STORES_INTERVAL = timedelta(days=1)
DOUBT_TIME = timedelta(hours=6)
KEEP_TIME = timedelta(hours=24)
TRUST_COUNT = 20
WATCH_DELAY = 5
FOLDER_TIME = timedelta(hours=6)
SEARCH_TIME = timedelta(minutes=10)
SUGGEST_TIMEOUT = 5
LIVE_ITEMS = 100
COUNT_ITEMS = 1000
FOLDER_ITEMS = 20
CATEGORY_DEALS = 30
ALL_DEALS = 50
STORE_DEALS = 10
THEME_DEALS = 50
DEAL_STORES = 10
FOUND_PAGES = 50
type Fetch[T] = Callable[[], Awaitable[T]]
_START = attrgetter("valid_from")
_RATIO = attrgetter("ratio")


class Cache(dict[str, tuple[datetime, Any]]):
    def __init__(self, gate: asyncio.Semaphore) -> None:
        super().__init__()
        self.gate = gate


def _shown(folders: list[Folder], now: datetime) -> list[Folder]:
    current = [folder for folder in folders if folder.valid_from <= now]
    first = max(current, key=_START) if current else min(folders, key=_START)
    return [first, *sorted((folder for folder in folders if folder is not first), key=_START)]


def _ranked(offers: Iterable[Offer]) -> list[Offer]:
    kept: dict[tuple[Any, ...], Offer] = {}
    for offer in sorted(offers, key=_RATIO):
        kept.setdefault((offer.store_id, offer.title.casefold(), offer.price, offer.sale_price), offer)
    return list(kept.values())


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
class Answers:
    time: datetime
    listed: datetime
    catalog: Catalog
    folders: list[Folder]
    featured: frozenset[str]
    found: dict[str, Found]
    hits: dict[str, dict[str, tuple[int, ...]]]
    deals: list[Offer]


@dataclass(frozen=True, slots=True)
class FoldersData:
    stores: dict[str, Store]
    categories: dict[str, Category]
    themes: dict[str, Category]
    folders: dict[str, list[Folder]]
    index: dict[str, Folder]
    followed: frozenset[str]
    featured: frozenset[str]
    watches: dict[str, Watch]
    matches: dict[str, list[Offer]]
    offered: dict[str, frozenset[str]]
    offers: list[Offer]
    mentions: dict[str, list[Hit]]
    deals: list[Offer]
    near: dict[str, Near]
    trusted: datetime

    def rank(self, offer: Offer) -> tuple[Any, ...]:
        near = self.near.get(offer.store_id)
        store = self.stores[offer.store_id].name.casefold()
        return offer.ratio, near is None, near[0] if near else 0.0, store, offer.title.casefold()

    def best(self, text: str) -> Offer | None:
        return min(self.matches[text], key=self.rank, default=None)


class FoldersCoordinator(DataUpdateCoordinator[FoldersData]):
    config_entry: FoldersConfigEntry

    def __init__(self, hass: HomeAssistant, entry: FoldersConfigEntry) -> None:
        super().__init__(hass, LOGGER, config_entry=entry, name=DOMAIN, update_interval=UPDATE_INTERVAL)
        self.client = FoldersClient(async_get_clientsession(hass))
        self.shops = ShopList(self)
        self.watch = WatchList(hass)
        self.failing = False
        self._answers: Answers | None = None
        self._doubt: tuple[tuple[str, ...], datetime] | None = None
        live = asyncio.Semaphore(2)
        self._folders, self._searches, self._suggestions, self._texts, self._themes = (Cache(live) for _ in range(5))
        self._offers = Cache(asyncio.Semaphore(1))
        self._shared: dict[tuple[int, str], asyncio.Task[Any]] = {}
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

    @callback
    def _async_watch_refresh(self, _: datetime) -> None:
        self._unsub_watch = None
        self.config_entry.async_create_background_task(self.hass, self.async_refresh(), f"{DOMAIN} watch refresh")

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

    async def _async_answers(self, now: datetime, watches: list[Watch]) -> Answers:
        last = self._answers
        if last is None or now - last.listed >= STORES_INTERVAL:
            listed, catalog = now - STORES_INTERVAL if last is None else now, await self._async_catalog()
        else:
            listed, catalog = last.listed, last.catalog
        folders = await self.client.async_get_folders()
        featured = frozenset() if last is None else last.featured
        with suppress(FoldersError):
            featured = await self.client.async_get_featured()
        found: dict[str, Found] = {}
        for word in dict.fromkeys(watch.word for watch in watches):
            try:
                found[word] = await self.client.async_search(word)
            except QueryError:
                if last is not None and word in last.found:
                    found[word] = last.found[word]
        deals = [
            offer
            for request in self._deal_requests(catalog, followed_stores(self.config_entry.options, catalog[0]))
            for offer in await self.client.async_get_deals(**request)
        ]
        known = {} if last is None else last.hits
        hits = {
            word: known[word] if result.folders is None else result.folders
            for word, result in found.items()
            if result.folders is not None or word in known
        }
        return Answers(now, listed, catalog, folders, featured, found, hits, deals)

    def _doubts(self, answers: Answers, now: datetime) -> str | None:
        last = self._answers
        kind = tuple(
            name
            for name, count, before in (
                ("stores", len(answers.catalog[0]), len(last.catalog[0]) if last else 0),
                ("folders", len(answers.folders), len(last.folders) if last else 0),
            )
            if not count or (before >= TRUST_COUNT and count < before / 2)
        )
        doubt = self._doubt if self._doubt and self._doubt[0] == kind else (kind, now)
        self._doubt = doubt if kind and now - doubt[1] < DOUBT_TIME else None
        return f"folders.nl sent too few {' and '.join(kind)}" if self._doubt else None

    async def _async_update_data(self) -> FoldersData:
        now, watches = dt_util.utcnow(), self.watch.active
        try:
            answers = await self._async_answers(now, watches)
        except FoldersError as err:
            self._doubt, problem = None, str(err)
        else:
            problem = self._doubts(answers, now)
        if problem is None:
            if self.failing:
                LOGGER.info("folders.nl answers again, showing the current folders")
            self._answers, self.failing, self.update_interval = answers, False, UPDATE_INTERVAL
        else:
            last, self.update_interval = self._answers, RETRY_INTERVAL
            if last is None or now - last.time >= KEEP_TIME:
                self.failing = True
                raise UpdateFailed(
                    translation_domain=DOMAIN,
                    translation_key="update_failed",
                    translation_placeholders={"error": problem},
                )
            if not self.failing:
                shown = dt_util.as_local(last.time).strftime("%Y-%m-%d %H:%M")
                LOGGER.warning("folders.nl does not answer as expected (%s), showing the folders of %s", problem, shown)
            self.failing, answers = True, last
        data = self._build(answers, now, watches)
        if data.watches:
            self.shops.async_start(dt_util.utcnow(), data.stores.values())
        return data

    @callback
    def async_shops_loaded(self) -> None:
        if self._answers is not None and self.data is not None:
            self.async_set_updated_data(self._build(self._answers, dt_util.utcnow(), self.watch.active))

    def _build(self, answers: Answers, now: datetime, active: list[Watch]) -> FoldersData:
        options, (stores, categories, themes) = self.config_entry.options, answers.catalog
        followed = followed_stores(options, stores)
        hidden = set(options.get(CONF_EXCLUDED_THEMES, []))
        index = {
            folder.folder_id: folder
            for folder in answers.folders
            if folder.store_id in stores and folder.valid_until > now and hidden.isdisjoint(folder.themes)
        }
        grouped: dict[str, list[Folder]] = {}
        for folder in index.values():
            grouped.setdefault(folder.store_id, []).append(folder)
        watched = stores if options.get(CONF_WATCH_ALL) else followed
        watches = {watch.text: watch for watch in active if watch.word in answers.found}
        matches = {
            text: [
                replace(offer, word=watch.word, limit=watch.limit)
                for offer in current_offers(answers.found[watch.word].offers, index, watched, now)
                if watch.wants(offer)
            ]
            for text, watch in watches.items()
        }
        offered = {
            text: frozenset(offer.folder_id for offer in answers.found[watch.word].offers)
            for text, watch in watches.items()
        }
        offers = unique(offer for items in matches.values() for offer in items)
        config = self.hass.config
        return FoldersData(
            stores,
            categories,
            themes,
            {store_id: _shown(items, now) for store_id, items in grouped.items()},
            index,
            followed,
            answers.featured.intersection(index),
            watches,
            matches,
            offered,
            sorted(offers, key=lambda offer: (stores[offer.store_id].name.casefold(), offer.title.casefold())),
            {
                text: _mentions(offered[text], answers.hits[watch.word], index, watched, stores)
                for text, watch in watches.items()
                if watch.limit is None and watch.word in answers.hits
            },
            _ranked(current_offers(answers.deals, index, followed, now)),
            self.shops.nearest({offer.store_id for offer in offers}, config.latitude, config.longitude),
            answers.time,
        )

    async def _async_live[T](
        self, cache: Cache, key: str, age: timedelta, fetch: Fetch[T], size: int = LIVE_ITEMS
    ) -> T:
        if (cached := cache.get(key)) is None or dt_util.utcnow() - cached[0] >= age:
            async with cache.gate:
                cached = (dt_util.utcnow(), await fetch())
            cache.pop(key, None)
            cache[key] = cached
            while len(cache) > size:
                del cache[next(iter(cache))]
        return cached[1]

    async def async_search(self, text: str) -> Found:
        return await self._async_live(self._searches, text, SEARCH_TIME, partial(self.client.async_search, text))

    async def async_suggest(self, text: str) -> list[tuple[str, str]]:
        fetch = partial(self.client.async_suggest, text)
        try:
            async with asyncio.timeout(SUGGEST_TIMEOUT):
                return await self._async_live(self._suggestions, text, SEARCH_TIME, fetch)
        except TimeoutError:
            raise FoldersError("The suggestions took too long") from None

    async def _async_shared[T](self, cache: Cache, key: str, age: timedelta, fetch: Fetch[T], size: int) -> T:
        if (cached := cache.get(key)) and dt_util.utcnow() - cached[0] < age:
            return cached[1]
        if (task := self._shared.get(slot := (id(cache), key))) is None:
            live = self._async_live(cache, key, age, fetch, size)
            task = self._shared[slot] = self.config_entry.async_create_background_task(self.hass, live, DOMAIN)
            task.add_done_callback(partial(self._shared_done, slot))
        await asyncio.wait((task,))
        if task.cancelled():
            raise FoldersError("Folders was unloaded")
        return task.result()

    def _shared_done(self, slot: tuple[int, str], task: asyncio.Task[Any]) -> None:
        del self._shared[slot]
        if not task.cancelled():
            task.exception()

    async def async_folder(self, folder: Folder) -> int:
        fetch = partial(self.client.async_get_folder, folder)
        return await self._async_shared(self._folders, folder.folder_id, timedelta.max, fetch, COUNT_ITEMS)

    async def async_folder_offers(self, folder: Folder) -> list[Offer]:
        fetch = partial(self.client.async_get_folder_offers, folder)
        return await self._async_shared(self._offers, folder.folder_id, FOLDER_TIME, fetch, FOLDER_ITEMS)

    async def async_find(self, folder: Folder, text: str) -> list[int] | None:
        async def fetch() -> tuple[str, ...]:
            texts = await self.client.async_get_text(folder)
            return await self.hass.async_add_executor_job(lambda: tuple(map(plain, texts)))

        pages = await self._async_live(self._texts, folder.folder_id, FOLDER_TIME, fetch, FOLDER_ITEMS)
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
        return _ranked(current_offers(offers, data.index, data.followed, dt_util.utcnow()))

    def page_count(self, folder_id: str) -> int | None:
        return cached[1] if (cached := self._folders.get(folder_id)) else None
