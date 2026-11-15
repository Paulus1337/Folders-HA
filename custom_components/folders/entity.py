from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import WEB_URL, Folder
from .const import ATTRIBUTION, DOMAIN, NAME
from .coordinator import FoldersCoordinator


def period(folder: Folder) -> dict[str, Any]:
    return {
        "valid_from": folder.valid_from.isoformat(),
        "valid_until": folder.valid_until.isoformat(),
        "url": folder.url,
    }


class FoldersEntity(CoordinatorEntity[FoldersCoordinator]):
    _attr_attribution = ATTRIBUTION
    _attr_has_entity_name = True

    def __init__(self, coordinator: FoldersCoordinator, key: str) -> None:
        super().__init__(coordinator)
        entry_id = coordinator.config_entry.entry_id
        self._attr_unique_id = f"{entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name=NAME,
            manufacturer="folders.nl",
            model=NAME,
            entry_type=DeviceEntryType.SERVICE,
            configuration_url=WEB_URL,
        )
