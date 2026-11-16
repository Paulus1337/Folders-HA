from __future__ import annotations

from contextlib import suppress
from pathlib import Path

from homeassistant.components import websocket_api
from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType
from homeassistant.loader import async_get_integration
import voluptuous as vol

from .api import FoldersError
from .const import (
    CONF_ALWAYS_STORES,
    CONF_EXCLUDED_CATEGORIES,
    CONF_EXCLUDED_STORES,
    CONF_EXCLUDED_THEMES,
    CONF_STORES,
    CONF_WATCH_ALL,
    CONF_WORDS,
    DEAL_LIMIT,
    DOMAIN,
    SCOPES,
    SEARCH_LIMIT,
)
from .coordinator import FoldersConfigEntry, FoldersCoordinator
from .shops import shop_storage
from .views import (
    FoldersImageView,
    async_search_answer,
    loaded_coordinator,
    offer_row,
    search_text,
    websocket_area,
    websocket_find,
    websocket_nearest,
    websocket_offers,
    websocket_overview,
    websocket_pages,
    websocket_search,
    websocket_shops,
    websocket_suggest,
)
from .watch import WatchList, watch_storage

PLATFORMS = [Platform.CALENDAR, Platform.EVENT, Platform.IMAGE, Platform.SENSOR, Platform.TODO]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
CARD_URL = f"/{DOMAIN}/folders-card.js"
CARD_PATH = Path(__file__).parent / "frontend" / "folders-card.js"
SEARCH_SCHEMA = vol.Schema(
    {
        vol.Required("query"): search_text,
        vol.Optional("scope", default=SCOPES[0]): vol.In(SCOPES),
        vol.Optional("limit", default=10): vol.All(vol.Coerce(int), vol.Range(min=1, max=SEARCH_LIMIT)),
    }
)
DEALS_SCHEMA = vol.Schema(
    {
        vol.Optional("limit", default=10): vol.All(vol.Coerce(int), vol.Range(min=1, max=DEAL_LIMIT)),
        vol.Optional("category"): cv.string,
        vol.Optional("theme"): cv.string,
    }
)


def _loaded(hass: HomeAssistant) -> FoldersCoordinator:
    if (coordinator := loaded_coordinator(hass)) is None:
        raise ServiceValidationError(translation_domain=DOMAIN, translation_key="not_loaded")
    return coordinator


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    async def async_search(call: ServiceCall) -> ServiceResponse:
        coordinator, limit = _loaded(hass), call.data["limit"]
        try:
            answer = await async_search_answer(coordinator, call.data["query"], call.data["scope"])
        except FoldersError as err:
            raise HomeAssistantError(translation_domain=DOMAIN, translation_key="unavailable") from err
        results = answer["results"]
        return {
            "results": results[:limit],
            "more": answer["more"] or len(results) > limit,
            "folders": answer["folders"],
        }

    async def async_best_deals(call: ServiceCall) -> ServiceResponse:
        coordinator = _loaded(hass)
        category, theme = call.data.get("category"), call.data.get("theme")
        for value, known, key in (
            (category, coordinator.data.categories, "unknown_category"),
            (theme, coordinator.data.themes, "unknown_theme"),
        ):
            if value is not None and value not in known:
                raise ServiceValidationError(translation_domain=DOMAIN, translation_key=key)
        try:
            deals = await coordinator.async_deals(theme)
        except FoldersError as err:
            raise HomeAssistantError(translation_domain=DOMAIN, translation_key="unavailable") from err
        data = coordinator.data
        chosen = [offer for offer in deals if category is None or category in data.stores[offer.store_id].categories]
        return {"deals": [offer_row(data, offer) for offer in chosen[: call.data["limit"]]]}

    hass.services.async_register(
        DOMAIN, "search", async_search, schema=SEARCH_SCHEMA, supports_response=SupportsResponse.ONLY
    )
    hass.services.async_register(
        DOMAIN, "best_deals", async_best_deals, schema=DEALS_SCHEMA, supports_response=SupportsResponse.ONLY
    )
    for command in (
        websocket_shops,
        websocket_nearest,
        websocket_area,
        websocket_overview,
        websocket_pages,
        websocket_offers,
        websocket_search,
        websocket_suggest,
        websocket_find,
    ):
        websocket_api.async_register_command(hass, command)
    hass.http.register_view(FoldersImageView())
    await hass.http.async_register_static_paths([StaticPathConfig(CARD_URL, str(CARD_PATH), cache_headers=False)])
    add_extra_js_url(hass, f"{CARD_URL}?v={(await async_get_integration(hass, DOMAIN)).version}")
    return True


async def async_migrate_entry(hass: HomeAssistant, entry: FoldersConfigEntry) -> bool:
    if entry.version == 1 and entry.minor_version < 2:
        watch = WatchList(hass)
        await watch.async_load()
        for word in entry.options.get(CONF_WORDS, []):
            with suppress(HomeAssistantError):
                await watch.async_add(word)
        options = {
            CONF_EXCLUDED_CATEGORIES: [],
            CONF_EXCLUDED_STORES: [],
            CONF_ALWAYS_STORES: list(entry.options.get(CONF_STORES, [])),
            CONF_EXCLUDED_THEMES: [],
            CONF_WATCH_ALL: False,
        }
        hass.config_entries.async_update_entry(entry, options=options, minor_version=2)
    return entry.version == 1


async def async_setup_entry(hass: HomeAssistant, entry: FoldersConfigEntry) -> bool:
    coordinator = FoldersCoordinator(hass, entry)
    await coordinator.watch.async_load()
    await coordinator.shops.async_load()
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: FoldersConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: FoldersConfigEntry) -> None:
    await shop_storage(hass).async_remove()
    await watch_storage(hass).async_remove()
