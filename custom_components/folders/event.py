from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.event import EventEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import EVENT_NEW_FOLDER, EVENT_NEW_OFFER
from .coordinator import FoldersConfigEntry, FoldersCoordinator
from .entity import FoldersEntity, period

PARALLEL_UPDATES = 0

type Item = tuple[datetime, datetime, dict[str, Any]]


async def async_setup_entry(
    hass: HomeAssistant, entry: FoldersConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    async_add_entities([FoldersEvent(entry.runtime_data)])


class FoldersEvent(FoldersEntity, EventEntity):
    _attr_translation_key = "folders"

    def __init__(self, coordinator: FoldersCoordinator) -> None:
        super().__init__(coordinator, "folders")
        self._attr_event_types = [EVENT_NEW_FOLDER, EVENT_NEW_OFFER]
        self._seen = {key: item[1] for key, item in self._items().items()}

    @property
    def available(self) -> bool:
        return True

    def _items(self) -> dict[tuple[str, str], Item]:
        data = self.coordinator.data
        items: dict[tuple[str, str], Item] = {}
        for store_id in self.coordinator.followed:
            for folder in data.folders.get(store_id, []):
                attributes = {"store": data.stores[store_id].name, "folder": folder.name or None, **period(folder)}
                items[EVENT_NEW_FOLDER, folder.folder_id] = (folder.valid_from, folder.valid_until, attributes)
        for offer in data.offers:
            attributes = {
                "store": data.stores[offer.store_id].name,
                "title": offer.title,
                "price": offer.price,
                "sale_price": offer.sale_price,
                "word": offer.word,
                "url": offer.url,
            }
            items[EVENT_NEW_OFFER, offer.offer_id] = (offer.valid_from, offer.valid_until, attributes)
        return items

    @callback
    def _handle_coordinator_update(self) -> None:
        now = dt_util.utcnow()
        self._seen = {key: until for key, until in self._seen.items() if until > now}
        new = [(key, item) for key, item in self._items().items() if key not in self._seen and item[1] > now]
        for key, (_start, until, attributes) in sorted(new, key=lambda pair: pair[1][0]):
            self._seen[key] = until
            self._trigger_event(key[0], attributes)
            self.async_write_ha_state()
        if not new:
            super()._handle_coordinator_update()
