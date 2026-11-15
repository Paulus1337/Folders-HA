from __future__ import annotations

from collections.abc import Callable, Mapping
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
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
)
import voluptuous as vol

from .api import FoldersClient, FoldersError, Store
from .const import CONF_STORES, CONF_WORDS, DOMAIN, MAX_STORES, MAX_WORDS, NAME
from .coordinator import FoldersConfigEntry


def _schema(stores: dict[str, Store]) -> vol.Schema:
    options = [
        SelectOptionDict(value=store.store_id, label=store.name)
        for store in sorted(stores.values(), key=lambda store: store.name.casefold())
    ]
    choice = SelectSelector(SelectSelectorConfig(options=options, multiple=True, mode=SelectSelectorMode.DROPDOWN))
    return vol.Schema(
        {vol.Optional(CONF_STORES, default=[]): choice, vol.Optional(CONF_WORDS, default=""): TextSelector()}
    )


def _words(text: str) -> list[str] | None:
    words = list(dict.fromkeys(word for part in text.split(",") if (word := " ".join(part.split()).lower())))
    return words if len(words) <= MAX_WORDS and all(2 <= len(word) <= 40 for word in words) else None


async def _async_step(
    flow: FoldersConfigFlow | FoldersOptionsFlow,
    step_id: str,
    user_input: dict[str, Any] | None,
    current: Mapping[str, Any],
    finish: Callable[[dict[str, Any]], ConfigFlowResult],
) -> ConfigFlowResult:
    if flow.stores is None:
        with suppress(FoldersError):
            flow.stores = await FoldersClient(async_get_clientsession(flow.hass)).async_get_stores()
        if flow.stores is None:
            return flow.async_show_form(step_id=step_id, errors={"base": "cannot_connect"})
        user_input = None
    errors: dict[str, str] = {}
    if user_input is not None:
        stores = list(dict.fromkeys(user_input.get(CONF_STORES, [])))
        words = _words(user_input.get(CONF_WORDS, ""))
        if len(stores) > MAX_STORES:
            errors[CONF_STORES] = "too_many_stores"
        if words is None:
            errors[CONF_WORDS] = "words"
        if not errors:
            return finish({CONF_STORES: stores, CONF_WORDS: words})
    suggested = user_input or {
        CONF_STORES: [store_id for store_id in current.get(CONF_STORES, []) if store_id in flow.stores],
        CONF_WORDS: ", ".join(current.get(CONF_WORDS, [])),
    }
    schema = flow.add_suggested_values_to_schema(_schema(flow.stores), suggested)
    return flow.async_show_form(step_id=step_id, data_schema=schema, errors=errors)


class FoldersConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self.stores: dict[str, Store] | None = None

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
        self.stores: dict[str, Store] | None = None

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        entry: FoldersConfigEntry = self.config_entry
        if self.stores is None and entry.state is ConfigEntryState.LOADED:
            self.stores = entry.runtime_data.data.stores
        return await _async_step(
            self, "init", user_input, entry.options, lambda options: self.async_create_entry(data=options)
        )
