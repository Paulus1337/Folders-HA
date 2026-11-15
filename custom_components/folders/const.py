from __future__ import annotations

import logging

DOMAIN = "folders"
LOGGER = logging.getLogger(__package__)
NAME = "Folders"
ATTRIBUTION = "Folders from folders.nl"

CONF_STORES = "stores"
CONF_WORDS = "words"

MAX_STORES = 60
MAX_WORDS = 10
OTHER_FOLDERS = 5
OFFER_LIMIT = 50
MAX_SHOPS = 300
MAX_BOX = 1.5

EVENT_NEW_FOLDER = "new_folder"
EVENT_NEW_OFFER = "new_offer"
