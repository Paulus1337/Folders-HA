from __future__ import annotations

from datetime import datetime
import re

from homeassistant.components.todo import TodoItem, TodoItemStatus, TodoListEntity, TodoListEntityFeature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .api import starts_with_store
from .coordinator import FoldersConfigEntry, FoldersCoordinator, FoldersData
from .entity import FoldersEntity

PARALLEL_UPDATES = 0
_MARKDOWN = re.compile(r"[!-/:-@\[-`{-~]")
TEXTS = {
    "en": (
        "No offer right now",
        "Mentioned in",
        "until",
        "page",
        ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"),
        ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"),
    ),
    "nl": (
        "Nu geen aanbieding",
        "Genoemd in",
        "t/m",
        "pagina",
        ("ma", "di", "wo", "do", "vr", "za", "zo"),
        ("jan", "feb", "mrt", "apr", "mei", "jun", "jul", "aug", "sep", "okt", "nov", "dec"),
    ),
}


async def async_setup_entry(
    hass: HomeAssistant, entry: FoldersConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    async_add_entities([FoldersWatchList(entry.runtime_data)])


def _plain(text: str) -> str:
    return _MARKDOWN.sub(r"\\\g<0>", text)


def describe(data: FoldersData, word: str, language: str) -> str:
    none, mentioned, until, page, days, months = TEXTS["nl" if language.startswith("nl") else "en"]

    def day(moment: datetime) -> str:
        local = dt_util.as_local(moment)
        return f"{until} {days[local.weekday()]} {local.day} {months[local.month - 1]}"

    if (offer := data.best.get(word)) is not None:
        prices = list(dict.fromkeys(f"{price:.2f}" for price in (offer.sale_price, offer.price) if price))
        price = f", {prices[0]} (was {prices[1]})" if len(prices) == 2 else "".join(f", {item}" for item in prices)
        number = f", {page} {offer.page}" if offer.page else ""
        return f"{_plain(data.stores[offer.store_id].name)}: {_plain(offer.title)}{price}, {day(offer.valid_until)}{number}"
    if hits := data.mentions.get(word):
        folder, pages = hits[0]
        store = data.stores[folder.store_id].name
        name = _plain(folder.name or store)
        if folder.name and not starts_with_store(folder.name, store):
            name += f" ({_plain(store)})"
        return f"{mentioned} {name}, {page} {pages[0]}, {day(folder.valid_until)}"
    return none


class FoldersWatchList(FoldersEntity, TodoListEntity):
    _attr_translation_key = "watch_list"
    _attr_supported_features = (
        TodoListEntityFeature.CREATE_TODO_ITEM
        | TodoListEntityFeature.UPDATE_TODO_ITEM
        | TodoListEntityFeature.DELETE_TODO_ITEM
        | TodoListEntityFeature.MOVE_TODO_ITEM
    )

    def __init__(self, coordinator: FoldersCoordinator) -> None:
        super().__init__(coordinator, "watch_list")
        self._attr_todo_items = self._items()

    @property
    def available(self) -> bool:
        return True

    def _items(self) -> list[TodoItem]:
        data, language = self.coordinator.data, self.coordinator.hass.config.language
        return [
            TodoItem(
                summary=item.word,
                uid=item.uid,
                status=TodoItemStatus.COMPLETED if item.paused else TodoItemStatus.NEEDS_ACTION,
                description=None if item.paused or item.word not in data.best else describe(data, item.word, language),
            )
            for item in self.coordinator.watch.items
        ]

    @callback
    def _handle_coordinator_update(self) -> None:
        self._attr_todo_items = self._items()
        super()._handle_coordinator_update()

    @callback
    def _async_changed(self) -> None:
        self.coordinator.async_watch_changed()
        self._handle_coordinator_update()

    async def async_create_todo_item(self, item: TodoItem) -> None:
        await self.coordinator.watch.async_add(item.summary or "", item.status == TodoItemStatus.COMPLETED)
        self._async_changed()

    async def async_update_todo_item(self, item: TodoItem) -> None:
        paused = item.status == TodoItemStatus.COMPLETED
        await self.coordinator.watch.async_update(item.uid or "", item.summary or "", paused)
        self._async_changed()

    async def async_delete_todo_items(self, uids: list[str]) -> None:
        await self.coordinator.watch.async_delete(uids)
        self._async_changed()

    async def async_move_todo_item(self, uid: str, previous_uid: str | None = None) -> None:
        await self.coordinator.watch.async_move(uid, previous_uid)
        self._handle_coordinator_update()
