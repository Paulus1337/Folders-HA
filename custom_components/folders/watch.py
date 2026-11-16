from __future__ import annotations

from collections.abc import Collection
from dataclasses import dataclass
import re
from typing import Any
from uuid import uuid4

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import storage

from .api import Offer
from .const import DOMAIN, MAX_WORDS

_LIMIT = re.compile(r"(.*?) ?(?:<|(?<!\S)(?:max|under|onder)) ?\u20ac? ?([0-9.,]+)")
_PRICE = re.compile(r"([0-9]{1,4})(?:[.,]([0-9]{1,2}))?")
MAX_CENTS = 999900


def watch_storage(hass: HomeAssistant) -> storage.Store[dict[str, Any]]:
    return storage.Store(hass, 1, f"{DOMAIN}.watch_list")


def clean(text: str) -> str | None:
    word = " ".join(text.split()).lower()
    return word if 2 <= len(word) <= 40 else None


@dataclass(frozen=True, slots=True)
class Watch:
    word: str
    limit: float | None = None

    @property
    def text(self) -> str:
        return self.word if self.limit is None else f"{self.word} < {self.limit:.2f}"

    def wants(self, offer: Offer) -> bool:
        price = offer.sale_price or offer.price
        return self.limit is None or (price is not None and round(price * 100) <= round(self.limit * 100))


def parse(text: str) -> Watch:
    words, limit = " ".join(text.split()).lower(), None
    if found := _LIMIT.fullmatch(words):
        words, price = found[1], _PRICE.fullmatch(found[2])
        cents = int(price[1]) * 100 + int((price[2] or "0").ljust(2, "0")) if price else 0
        if not 1 <= cents <= MAX_CENTS:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="invalid_limit")
        limit = cents / 100
    if (word := clean(words)) is None:
        raise ServiceValidationError(translation_domain=DOMAIN, translation_key="invalid_word")
    return Watch(word, limit)


@dataclass(slots=True)
class WatchItem:
    uid: str
    watch: Watch
    paused: bool = False


class WatchList:
    def __init__(self, hass: HomeAssistant) -> None:
        self._storage = watch_storage(hass)
        self.items: list[WatchItem] = []

    @property
    def active(self) -> list[Watch]:
        return [item.watch for item in self.items if not item.paused]

    @property
    def words(self) -> list[str]:
        return [watch.text for watch in self.active]

    async def async_load(self) -> None:
        stored = await self._storage.async_load()
        rows = stored.get("items") if isinstance(stored, dict) else None
        for row in rows if isinstance(rows, list) else []:
            data = row if isinstance(row, dict) else {}
            uid, text, paused = data.get("uid"), data.get("word"), data.get("paused")
            if not (isinstance(uid, str) and isinstance(text, str) and isinstance(paused, bool)):
                continue
            try:
                watch = parse(text)
            except ServiceValidationError:
                continue
            if all(watch != item.watch and uid != item.uid for item in self.items):
                self.items.append(WatchItem(uid, watch, paused))

    async def _async_save(self) -> None:
        rows = [{"uid": item.uid, "word": item.watch.text, "paused": item.paused} for item in self.items]
        await self._storage.async_save({"items": rows})

    def _find(self, uid: str) -> WatchItem:
        if (found := next((item for item in self.items if item.uid == uid), None)) is None:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="item_not_found")
        return found

    def _check(self, text: str, paused: bool, item: WatchItem | None = None) -> Watch:
        watch = parse(text)
        others = [other for other in self.items if other is not item]
        if any(other.watch == watch for other in others):
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="duplicate_word")
        if not paused and sum(not other.paused for other in others) >= MAX_WORDS:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="too_many_words",
                translation_placeholders={"limit": str(MAX_WORDS)},
            )
        return watch

    async def async_add(self, text: str, paused: bool = False) -> None:
        self.items.append(WatchItem(uuid4().hex, self._check(text, paused), paused))
        await self._async_save()

    async def async_update(self, uid: str, text: str, paused: bool) -> None:
        item = self._find(uid)
        item.watch, item.paused = self._check(text, paused, item), paused
        await self._async_save()

    async def async_delete(self, uids: Collection[str]) -> None:
        self.items = [item for item in self.items if item.uid not in uids]
        await self._async_save()

    async def async_move(self, uid: str, previous: str | None) -> None:
        item, after = self._find(uid), self._find(previous) if previous else None
        if item is not after:
            self.items.remove(item)
            self.items.insert(self.items.index(after) + 1 if after else 0, item)
            await self._async_save()
