from __future__ import annotations

import logging

DOMAIN = "folders"
LOGGER = logging.getLogger(__package__)
NAME = "Folders"
ATTRIBUTION = "Folders from folders.nl"

CONF_EXCLUDED_CATEGORIES = "excluded_categories"
CONF_EXCLUDED_STORES = "excluded_stores"
CONF_ALWAYS_STORES = "always_stores"
CONF_EXCLUDED_THEMES = "excluded_themes"
CONF_WATCH_ALL = "watch_all"
CONF_STORES = "stores"
CONF_WORDS = "words"
OTHER = "other"
SCOPES = ("all", "followed")

OTHER_FOLDERS = 5
OFFER_LIMIT = 50
DEAL_LIMIT = 30
OVERVIEW_DEALS = 60
MENTION_LIMIT = 50
WORD_MENTIONS = 10
SEARCH_LIMIT = 60
HIT_LIMIT = 30
NEAREST_LIMIT = 50
STORE_IDS = 60
MAX_WORDS = 20
MAX_SHOPS = 300
MAX_BOX = 1.5

EVENT_NEW_FOLDER = "new_folder"
EVENT_NEW_OFFER = "new_offer"
EVENT_NEW_MENTION = "new_mention"
