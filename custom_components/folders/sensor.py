from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DEAL_LIMIT, OFFER_LIMIT
from .coordinator import FoldersConfigEntry, FoldersCoordinator
from .entity import FoldersEntity, offer_attributes

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant, entry: FoldersConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    async_add_entities([FoldersOffers(entry.runtime_data), FoldersDeals(entry.runtime_data)])


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
            "words": list(data.words),
            "offers": [
                {**offer_attributes(data, offer), "description": offer.description}
                for offer in data.offers[:OFFER_LIMIT]
            ],
        }


class FoldersDeals(FoldersEntity, SensorEntity):
    _attr_translation_key = "best_deals"
    _unrecorded_attributes = frozenset({"deals"})

    def __init__(self, coordinator: FoldersCoordinator) -> None:
        super().__init__(coordinator, "best_deals")

    @property
    def native_value(self) -> int:
        return len(self.coordinator.data.deals)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        data = self.coordinator.data
        return {"deals": [offer_attributes(data, offer) for offer in data.deals[:DEAL_LIMIT]]}
