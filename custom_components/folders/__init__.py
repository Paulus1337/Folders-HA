from __future__ import annotations

from pathlib import Path

from homeassistant.components import websocket_api
from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType
from homeassistant.loader import async_get_integration

from .const import DOMAIN
from .coordinator import FoldersConfigEntry, FoldersCoordinator
from .shops import shop_storage
from .views import FoldersImageView, websocket_shops

PLATFORMS = [Platform.EVENT, Platform.IMAGE, Platform.SENSOR]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
CARD_URL = f"/{DOMAIN}/folders-card.js"
CARD_PATH = Path(__file__).parent / "frontend" / "folders-card.js"


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    websocket_api.async_register_command(hass, websocket_shops)
    hass.http.register_view(FoldersImageView())
    await hass.http.async_register_static_paths([StaticPathConfig(CARD_URL, str(CARD_PATH), cache_headers=False)])
    add_extra_js_url(hass, f"{CARD_URL}?v={(await async_get_integration(hass, DOMAIN)).version}")
    return True


async def async_setup_entry(hass: HomeAssistant, entry: FoldersConfigEntry) -> bool:
    coordinator = FoldersCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    await coordinator.shops.async_load()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: FoldersConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: FoldersConfigEntry) -> None:
    await shop_storage(hass).async_remove()
