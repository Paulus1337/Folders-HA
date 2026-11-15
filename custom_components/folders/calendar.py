from __future__ import annotations

from datetime import datetime

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .api import starts_with_store
from .coordinator import FoldersConfigEntry, FoldersCoordinator
from .entity import FoldersEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant, entry: FoldersConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    async_add_entities([FoldersCalendar(entry.runtime_data)])


def _summary(name: str, store: str) -> str:
    if starts_with_store(name, store):
        return name
    return f"{store}: {name}" if name else store


class FoldersCalendar(FoldersEntity, CalendarEntity):
    _attr_translation_key = "folders"

    def __init__(self, coordinator: FoldersCoordinator) -> None:
        super().__init__(coordinator, "calendar")

    def _events(self) -> list[CalendarEvent]:
        data = self.coordinator.data
        events = [
            CalendarEvent(
                start=dt_util.as_local(folder.valid_from),
                end=dt_util.as_local(folder.valid_until),
                summary=_summary(folder.name, data.stores[store_id].name),
                description=folder.url,
                uid=folder.folder_id,
            )
            for store_id in data.followed
            for folder in data.folders.get(store_id, [])
        ]
        return sorted(events, key=lambda event: (event.start, event.summary, event.uid))

    @property
    def event(self) -> CalendarEvent | None:
        now = dt_util.utcnow()
        return next((event for event in self._events() if event.end > now), None)

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        return [event for event in self._events() if event.start < end_date and event.end > start_date]
