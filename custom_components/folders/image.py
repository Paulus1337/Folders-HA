from __future__ import annotations

from typing import Any

from homeassistant.components.image import Image, ImageEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .api import Folder, Store, async_get_image
from .coordinator import FoldersConfigEntry, FoldersCoordinator
from .entity import FoldersEntity, period

PARALLEL_UPDATES = 0
PAGE_LIMIT = 10 * 1024 * 1024


async def async_setup_entry(
    hass: HomeAssistant, entry: FoldersConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    registry = er.async_get(hass)
    for item in er.async_entries_for_config_entry(registry, entry.entry_id):
        if item.domain == "image" and item.unique_id.removeprefix(f"{entry.entry_id}_") not in coordinator.followed:
            registry.async_remove(item.entity_id)
    known: set[str] = set()

    @callback
    def async_add_stores() -> None:
        stores = coordinator.data.stores
        new = [stores[store_id] for store_id in coordinator.followed if store_id in stores and store_id not in known]
        known.update(store.store_id for store in new)
        if new:
            async_add_entities(FoldersImage(coordinator, store) for store in new)

    async_add_stores()
    entry.async_on_unload(coordinator.async_add_listener(async_add_stores))


class FoldersImage(FoldersEntity, ImageEntity):
    _attr_translation_key = "folder"
    _unrecorded_attributes = frozenset({"other_folders"})

    def __init__(self, coordinator: FoldersCoordinator, store: Store) -> None:
        FoldersEntity.__init__(self, coordinator, store.store_id)
        ImageEntity.__init__(self, coordinator.hass, verify_ssl=True)
        self._store_id = store.store_id
        self._attr_name = store.name
        self._shown: tuple[str, str | None] | None = None
        self._update()

    @property
    def _folders(self) -> list[Folder]:
        return self.coordinator.data.folders.get(self._store_id, [])

    def _update(self) -> None:
        folder = next(iter(self._folders), None)
        shown = (folder.folder_id, folder.image) if folder else None
        if shown != self._shown:
            self._shown, self._cached_image = shown, None
            self._attr_image_url = folder.image if folder else None
            self._attr_image_last_updated = dt_util.utcnow() if folder else None

    @callback
    def _handle_coordinator_update(self) -> None:
        self._update()
        super()._handle_coordinator_update()

    async def _async_load_image_from_url(self, url: str) -> Image | None:
        image = await async_get_image(async_get_clientsession(self.hass), url, PAGE_LIMIT)
        return Image(*image) if image else None

    @property
    def available(self) -> bool:
        return super().available and self._shown is not None

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        if not (folders := self._folders):
            return None
        folder, store = folders[0], self.coordinator.data.stores[self._store_id]
        return {
            "store": store.name,
            "folder": folder.name or None,
            **period(folder),
            "upcoming": folder.valid_from > dt_util.utcnow(),
            "store_url": store.url,
            "other_folders": [{"name": item.name or None, **period(item)} for item in folders[1:]],
        }
