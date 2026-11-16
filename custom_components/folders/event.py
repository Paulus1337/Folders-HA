from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from operator import attrgetter
from typing import Any

from homeassistant.components.event import EventEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .api import Folder, Offer
from .const import EVENT_NEW_FOLDER, EVENT_NEW_MENTION, EVENT_NEW_OFFER
from .coordinator import FoldersConfigEntry, FoldersCoordinator, FoldersData
from .entity import FoldersEntity, nearby, period

PARALLEL_UPDATES = 0
FRESH = timedelta(days=3)
OLD = datetime.min.replace(tzinfo=UTC)
_START = attrgetter("valid_from")

type Key = tuple[Any, ...]


def _folder(data: FoldersData, folder: Folder) -> dict[str, Any]:
    return {
        "store": data.stores[folder.store_id].name,
        "folder": folder.name or None,
        **period(folder),
        "folder_id": folder.folder_id,
    }


def _offer(data: FoldersData, offer: Offer, count: int) -> dict[str, Any]:
    return {
        "store": data.stores[offer.store_id].name,
        "title": offer.title,
        "price": offer.price,
        "sale_price": offer.sale_price,
        "description": offer.description,
        "word": offer.word,
        "limit": offer.limit,
        "url": offer.url,
        "folder_id": offer.folder_id,
        "page": offer.page,
        **nearby(data.near.get(offer.store_id)),
        "new_offers": count,
    }


def _mention(data: FoldersData, word: str, folder: Folder, pages: tuple[int, ...], count: int) -> dict[str, Any]:
    return {**_folder(data, folder), "word": word, "page": pages[0], "new_mentions": count}


async def async_setup_entry(
    hass: HomeAssistant, entry: FoldersConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    async_add_entities([FoldersEvent(entry.runtime_data)])


class FoldersEvent(FoldersEntity, EventEntity):
    _attr_translation_key = "folders"

    def __init__(self, coordinator: FoldersCoordinator) -> None:
        super().__init__(coordinator, "folders")
        self._attr_event_types = [EVENT_NEW_FOLDER, EVENT_NEW_OFFER, EVENT_NEW_MENTION]
        self._seen: dict[Key, datetime] = {}
        self._appeared = dict.fromkeys(coordinator.data.index, OLD)
        self._words = self._searched()
        self._news()

    @property
    def available(self) -> bool:
        return True

    def _searched(self) -> dict[str, set[str]]:
        data = self.coordinator.data
        return {EVENT_NEW_OFFER: set(data.watches), EVENT_NEW_MENTION: set(data.mentions)}

    def _new(self, until: datetime, now: datetime, *keys: Key) -> bool:
        new = until > now and self._seen.keys().isdisjoint(keys)
        for key in keys:
            self._seen.setdefault(key, until)
        return new

    def _news(self) -> list[tuple[str, dict[str, Any]]]:
        now, data, words = dt_util.utcnow(), self.coordinator.data, self._words
        fresh, self._words = now - FRESH, self._searched()
        self._seen = {key: until for key, until in self._seen.items() if until > now}
        self._appeared = {folder_id: self._appeared.get(folder_id, now) for folder_id in data.index}
        folders = (folder for store_id in sorted(data.followed) for folder in data.folders.get(store_id, []))
        news = [
            (EVENT_NEW_FOLDER, _folder(data, folder))
            for folder in sorted(folders, key=_START)
            if self._new(folder.valid_until, now, (EVENT_NEW_FOLDER, folder.folder_id))
        ]
        known = {
            text: {key for offer in data.matches[text] for key in offer.identity}
            for text in data.watches
            if text in words[EVENT_NEW_OFFER]
        }
        offers: dict[str, list[Offer]] = {}
        for offer in data.offers:
            text = next((text for text, keys in known.items() if not keys.isdisjoint(offer.identity)), None)
            if (
                self._new(offer.valid_until, now, *((EVENT_NEW_OFFER, key) for key in offer.identity))
                and text
                and max(offer.valid_from, self._appeared[offer.folder_id]) > fresh
            ):
                watch = data.watches[text]
                offers.setdefault(text, []).append(replace(offer, word=watch.word, limit=watch.limit))
        for text, watch in data.watches.items():
            for folder_id in data.index.keys() & data.offered[text]:
                self._seen.setdefault((EVENT_NEW_MENTION, text, folder_id), data.index[folder_id].valid_until)
            hits = [
                (folder, pages)
                for folder, pages in data.mentions.get(text, [])
                if self._new(folder.valid_until, now, (EVENT_NEW_MENTION, text, folder.folder_id))
                and self._appeared[folder.folder_id] > fresh
            ]
            if text in offers:
                news.append((EVENT_NEW_OFFER, _offer(data, min(offers[text], key=data.rank), len(offers[text]))))
            if hits and text in words[EVENT_NEW_MENTION]:
                news.append((EVENT_NEW_MENTION, _mention(data, watch.word, *hits[0], len(hits))))
        return news

    @callback
    def _handle_coordinator_update(self) -> None:
        news = self._news()
        for kind, attributes in news:
            self._trigger_event(kind, attributes)
            self.async_write_ha_state()
        if not news:
            super()._handle_coordinator_update()
