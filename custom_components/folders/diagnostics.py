from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from .const import (
    CONF_ALWAYS_STORES,
    CONF_EXCLUDED_CATEGORIES,
    CONF_EXCLUDED_STORES,
    CONF_EXCLUDED_THEMES,
    CONF_WATCH_ALL,
)
from .coordinator import FoldersConfigEntry


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: FoldersConfigEntry) -> dict[str, Any]:
    coordinator = entry.runtime_data
    data, shops, watch, options = coordinator.data, coordinator.shops, coordinator.watch, entry.options
    images = [
        item for item in er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id) if item.domain == "image"
    ]
    age = (dt_util.utcnow() - shops.updated).total_seconds() if shops.updated else None
    return {
        **{
            key: len(options.get(key, []))
            for key in (CONF_EXCLUDED_CATEGORIES, CONF_EXCLUDED_STORES, CONF_ALWAYS_STORES, CONF_EXCLUDED_THEMES)
        },
        "watch_all": options.get(CONF_WATCH_ALL, False),
        "followed_stores": len(data.followed),
        "watch_words": len(watch.words),
        "paused_words": len(watch.items) - len(watch.words),
        "stores": len(data.stores),
        "folders": len(data.index),
        "featured_folders": len(data.featured),
        "offers": len(data.offers),
        "mentions": sum(len(hits) for hits in data.mentions.values()),
        "deals": len(data.deals),
        "image_entities": len(images),
        "enabled_image_entities": sum(1 for item in images if not item.disabled),
        "shops": len(shops.shops),
        "shops_age_hours": None if age is None else round(age / 3600, 1),
        "last_update_success": coordinator.last_update_success,
    }
