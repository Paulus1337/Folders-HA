from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import OFFER_LIMIT
from .coordinator import FoldersConfigEntry, FoldersCoordinator
from .entity import FoldersEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant, entry: FoldersConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    async_add_entities([FoldersOffers(entry.runtime_data)])


class FoldersOffers(FoldersEntity, SensorEntity):
    _attr_translation_key = "offers"
    _unrecorded_attributes = frozenset({"offers"})

    def __init__(self, coordinator: FoldersCoordinator) -> None:
        super().__init__(coordinator, "offers")

    @property
    def native_value(self) -> int:
        return len(self.coordinator.data.offers)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data
        return {
            "words": self.coordinator.words,
            "offers": [
                {
                    "store": data.stores[offer.store_id].name,
                    "title": offer.title,
                    "price": offer.price,
                    "sale_price": offer.sale_price,
                    "valid_until": offer.valid_until.isoformat(),
                    "url": offer.url,
                    "page": offer.page,
                }
                for offer in data.offers[:OFFER_LIMIT]
            ],
        }
