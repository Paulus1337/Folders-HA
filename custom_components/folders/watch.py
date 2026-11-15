from __future__ import annotations

from collections.abc import Collection
from dataclasses import asdict, dataclass
from typing import Any
from uuid import uuid4

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import storage

from .const import DOMAIN, MAX_WORDS


def watch_storage(hass: HomeAssistant) -> storage.Store[dict[str, Any]]:
    return storage.Store(hass, 1, f"{DOMAIN}.watch_list")


def clean(text: str) -> str | None:
    word = " ".join(text.split()).lower()
    return word if 2 <= len(word) <= 40 else None


@dataclass(slots=True)
class WatchItem:
    uid: str
    word: str
    paused: bool = False


class WatchList:
    def __init__(self, hass: HomeAssistant) -> None:
        self._storage = watch_storage(hass)
        self.items: list[WatchItem] = []

    @property
    def words(self) -> list[str]:
        return [item.word for item in self.items if not item.paused]

    async def async_load(self) -> None:
        stored = await self._storage.async_load()
        rows = stored.get("items") if isinstance(stored, dict) else None
        for row in rows if isinstance(rows, list) else []:
            data = row if isinstance(row, dict) else {}
            uid, text, paused = data.get("uid"), data.get("word"), data.get("paused")
            if (
                isinstance(uid, str)
                and isinstance(text, str)
                and isinstance(paused, bool)
                and (word := clean(text))
                and all(word != item.word and uid != item.uid for item in self.items)
            ):
                self.items.append(WatchItem(uid, word, paused))

    async def _async_save(self) -> None:
        await self._storage.async_save({"items": [asdict(item) for item in self.items]})

    def _find(self, uid: str) -> WatchItem:
        if (found := next((item for item in self.items if item.uid == uid), None)) is None:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="item_not_found")
        return found

    def _check(self, text: str, paused: bool, item: WatchItem | None = None) -> str:
        if (word := clean(text)) is None:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="invalid_word")
        others = [other for other in self.items if other is not item]
        if any(other.word == word for other in others):
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="duplicate_word")
        if not paused and sum(not other.paused for other in others) >= MAX_WORDS:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="too_many_words",
                translation_placeholders={"limit": str(MAX_WORDS)},
            )
        return word

    async def async_add(self, text: str, paused: bool = False) -> None:
        self.items.append(WatchItem(uuid4().hex, self._check(text, paused), paused))
        await self._async_save()

    async def async_update(self, uid: str, text: str, paused: bool) -> None:
        item = self._find(uid)
        item.word, item.paused = self._check(text, paused, item), paused
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
