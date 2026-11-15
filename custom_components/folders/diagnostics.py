from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from .coordinator import FoldersConfigEntry


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: FoldersConfigEntry) -> dict[str, Any]:
    coordinator = entry.runtime_data
    data, shops = coordinator.data, coordinator.shops
    entities = er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
    age = (dt_util.utcnow() - shops.updated).total_seconds() if shops.updated else None
    return {
        "followed_stores": len(coordinator.followed),
        "words": len(coordinator.words),
        "stores": len(data.stores),
        "folders": sum(map(len, data.folders.values())),
        "offers": len(data.offers),
        "image_entities": sum(1 for item in entities if item.domain == "image"),
        "shops": len(shops.shops),
        "shops_age_hours": None if age is None else round(age / 3600, 1),
        "last_update_success": coordinator.last_update_success,
    }
