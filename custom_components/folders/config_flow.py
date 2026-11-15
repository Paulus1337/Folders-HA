from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from contextlib import suppress
from typing import Any

from homeassistant.config_entries import (
    ConfigEntryState,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
    OptionsFlowWithReload,
)
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    BooleanSelector,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)
import voluptuous as vol

from .api import Category, FoldersClient, FoldersError, Store
from .const import (
    CONF_ALWAYS_STORES,
    CONF_EXCLUDED_CATEGORIES,
    CONF_EXCLUDED_STORES,
    CONF_EXCLUDED_THEMES,
    CONF_WATCH_ALL,
    DOMAIN,
    NAME,
    OTHER,
)
from .coordinator import FoldersConfigEntry

type Catalog = tuple[dict[str, Store], dict[str, Category], dict[str, Category]]
LISTS = (CONF_EXCLUDED_CATEGORIES, CONF_EXCLUDED_STORES, CONF_ALWAYS_STORES, CONF_EXCLUDED_THEMES)


def _choices(items: Iterable[tuple[str, str]]) -> list[SelectOptionDict]:
    return [
        SelectOptionDict(value=value, label=label)
        for value, label in sorted(items, key=lambda item: item[1].casefold())
    ]


def _select(options: list[SelectOptionDict], **config: Any) -> SelectSelector:
    return SelectSelector(
        SelectSelectorConfig(options=options, multiple=True, mode=SelectSelectorMode.DROPDOWN, **config)
    )


def _schema(catalog: Catalog, options_flow: bool) -> vol.Schema:
    stores, categories, themes = catalog
    labels = [
        *_choices((category.slug, category.name) for category in categories.values()),
        SelectOptionDict(value=OTHER, label="Other"),
    ]
    names = _choices((store.store_id, store.name) for store in stores.values())
    schema: dict[Any, Any] = {
        vol.Optional(CONF_EXCLUDED_CATEGORIES, default=[]): _select(labels, translation_key="categories"),
        vol.Optional(CONF_EXCLUDED_STORES, default=[]): _select(names),
        vol.Optional(CONF_ALWAYS_STORES, default=[]): _select(names),
        vol.Optional(CONF_EXCLUDED_THEMES, default=[]): _select(
            _choices((theme.slug, theme.name) for theme in themes.values())
        ),
    }
    if options_flow:
        schema[vol.Optional(CONF_WATCH_ALL, default=False)] = BooleanSelector()
    return vol.Schema(schema)


async def _async_step(
    flow: FoldersConfigFlow | FoldersOptionsFlow,
    step_id: str,
    user_input: dict[str, Any] | None,
    current: Mapping[str, Any],
    finish: Callable[[dict[str, Any]], ConfigFlowResult],
) -> ConfigFlowResult:
    if flow.catalog is None:
        with suppress(FoldersError):
            client = FoldersClient(async_get_clientsession(flow.hass))
            stores = await client.async_get_stores()
            flow.catalog = (stores, await client.async_get_categories(), await client.async_get_themes())
        if flow.catalog is None:
            return flow.async_show_form(step_id=step_id, errors={"base": "cannot_connect"})
        user_input = None
    errors: dict[str, str] | None = None
    if user_input is not None:
        chosen = {key: list(dict.fromkeys(user_input.get(key, []))) for key in LISTS}
        options = {**chosen, CONF_WATCH_ALL: user_input.get(CONF_WATCH_ALL, False)}
        if set(chosen[CONF_ALWAYS_STORES]).isdisjoint(chosen[CONF_EXCLUDED_STORES]):
            return finish(options)
        current, errors = options, {CONF_ALWAYS_STORES: "always_excluded"}
    stores, categories, themes = flow.catalog
    known = {
        CONF_EXCLUDED_CATEGORIES: {*categories, OTHER},
        CONF_EXCLUDED_STORES: stores,
        CONF_ALWAYS_STORES: stores,
        CONF_EXCLUDED_THEMES: themes,
    }
    suggested = {key: [value for value in current.get(key, []) if value in known[key]] for key in LISTS}
    schema = _schema(flow.catalog, step_id == "init")
    schema = flow.add_suggested_values_to_schema(schema, {**suggested, CONF_WATCH_ALL: current.get(CONF_WATCH_ALL)})
    return flow.async_show_form(step_id=step_id, data_schema=schema, errors=errors)


class FoldersConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1
    MINOR_VERSION = 2

    def __init__(self) -> None:
        self.catalog: Catalog | None = None

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: FoldersConfigEntry) -> OptionsFlow:
        return FoldersOptionsFlow()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        return await _async_step(
            self, "user", user_input, {}, lambda options: self.async_create_entry(title=NAME, data={}, options=options)
        )


class FoldersOptionsFlow(OptionsFlowWithReload):
    def __init__(self) -> None:
        self.catalog: Catalog | None = None

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        entry: FoldersConfigEntry = self.config_entry
        if self.catalog is None and entry.state is ConfigEntryState.LOADED:
            data = entry.runtime_data.data
            self.catalog = (data.stores, data.categories, data.themes)
        return await _async_step(
            self, "init", user_input, entry.options, lambda options: self.async_create_entry(data=options)
        )
