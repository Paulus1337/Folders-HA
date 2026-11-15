from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from operator import attrgetter

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import Folder, FoldersClient, FoldersError, Offer, Store
from .const import CONF_STORES, CONF_WORDS, DOMAIN, LOGGER, OTHER_FOLDERS
from .shops import ShopList

type FoldersConfigEntry = ConfigEntry[FoldersCoordinator]

UPDATE_INTERVAL = timedelta(hours=3)
RETRY_INTERVAL = timedelta(minutes=15)
STORES_INTERVAL = timedelta(days=1)
_START = attrgetter("valid_from")


def _shown(folders: list[Folder], now: datetime) -> list[Folder]:
    current = [folder for folder in folders if folder.valid_from <= now]
    first = max(current, key=_START) if current else min(folders, key=_START)
    return [first, *sorted((folder for folder in folders if folder is not first), key=_START)[:OTHER_FOLDERS]]


@dataclass(frozen=True, slots=True)
class FoldersData:
    stores: dict[str, Store]
    folders: dict[str, list[Folder]]
    offers: list[Offer]


class FoldersCoordinator(DataUpdateCoordinator[FoldersData]):
    config_entry: FoldersConfigEntry

    def __init__(self, hass: HomeAssistant, entry: FoldersConfigEntry) -> None:
        super().__init__(hass, LOGGER, config_entry=entry, name=DOMAIN, update_interval=UPDATE_INTERVAL)
        self.followed: list[str] = list(entry.options.get(CONF_STORES, []))
        self.words: list[str] = list(entry.options.get(CONF_WORDS, []))
        self.client = FoldersClient(async_get_clientsession(hass))
        self.shops = ShopList(self)
        self._stores: tuple[datetime, dict[str, Store]] | None = None

    async def _async_update_data(self) -> FoldersData:
        now = dt_util.utcnow()
        try:
            if self._stores is None or now - self._stores[0] >= STORES_INTERVAL:
                self._stores = (now, await self.client.async_get_stores())
            folders = await self.client.async_get_folders()
            found = [offer for word in self.words for offer in await self.client.async_get_offers(word)]
        except FoldersError as err:
            self.update_interval = RETRY_INTERVAL
            raise UpdateFailed(
                translation_domain=DOMAIN, translation_key="update_failed", translation_placeholders={"error": str(err)}
            ) from err
        self.update_interval = UPDATE_INTERVAL
        stores = self._stores[1]
        current: dict[str, list[Folder]] = {}
        for folder in folders:
            if folder.store_id in stores and folder.valid_until > now:
                current.setdefault(folder.store_id, []).append(folder)
        offers: dict[str, Offer] = {}
        for offer in found:
            if (
                offer.store_id in self.followed
                and offer.store_id in stores
                and offer.valid_from <= now < offer.valid_until
            ):
                offers.setdefault(offer.offer_id, offer)
        return FoldersData(
            stores,
            {store_id: _shown(items, now) for store_id, items in current.items()},
            sorted(offers.values(), key=lambda offer: (stores[offer.store_id].name.casefold(), offer.title.casefold())),
        )
