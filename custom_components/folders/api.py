from __future__ import annotations

import asyncio
from collections.abc import Collection, Mapping
from dataclasses import dataclass
from datetime import datetime
from functools import partial
import json
import math
import re
from typing import Any
import unicodedata

import aiohttp

GRAPHQL_URL = "https://api.wepublish.digital/api/graphql/frontend"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
OVERPASS_AGENT = "Folders-HA (Home Assistant integration; +https://github.com/Paulus1337/Folders-HA)"
WEB_URL = "https://folders.nl"
AFFILIATE = "folders-nl"
FOLDERS_TIMEOUT = aiohttp.ClientTimeout(total=30)
OVERPASS_TIMEOUT = aiohttp.ClientTimeout(total=330)
FOLDERS_LIMIT = 4 * 1024 * 1024
OVERPASS_LIMIT = 64 * 1024 * 1024
IMAGE_MAGIC = (
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
)
PAGE_SIZE = 100
MAX_PAGES = 10
OFFER_PAGES = 3
RETRY_STATUSES = frozenset({429, 502, 503, 504})
RETRY_DELAYS = (30, 90)
TEXT_LIMIT = 200
OVERPASS_QUERY = (
    '[out:json][timeout:300];area["ISO3166-1"="NL"][admin_level=2]->.nl;nwr["shop"]["brand"~"^({names})$",i](area.nl);'
    'convert shop ::id=id(),::geom=center(geom()),kind=type(),brand=t["brand"],name=t["name"],street=t["addr:street"],'
    'housenumber=t["addr:housenumber"],city=t["addr:city"];out geom;'
)
REQUEST_ERRORS = (aiohttp.ClientError, TimeoutError, ValueError)
_ID = re.compile(r"[\w-]{1,64}", re.ASCII)
_SLUG = re.compile(r"[a-z0-9-]{1,120}")
_IMAGE = re.compile(r"https://(?:assets\.wepublish\.com|api\.wepublish\.digital)/[\w.~%/+=&?-]{1,2000}", re.ASCII)
_THUMB = re.compile(r"-thumb(?=\.\w+(?:\?|$))")
_SPECIAL = re.compile(r'[\\.^$|?*+()\[\]{}"]')
_OTHER = re.compile(r"[^a-z0-9]")
_KINDS = {"node": "n", "way": "w", "relation": "r"}


class FoldersError(Exception):
    pass


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _text(value: Any) -> str:
    return " ".join(value.split())[:TEXT_LIMIT].rstrip() if isinstance(value, str) else ""


def _match(pattern: re.Pattern[str], value: Any) -> str | None:
    return value if isinstance(value, str) and pattern.fullmatch(value) else None


def _number(value: Any) -> float | None:
    if isinstance(value, int) and not isinstance(value, bool) and abs(value) < 1e15:
        return float(value)
    return value if isinstance(value, float) and math.isfinite(value) else None


def _price(value: Any) -> float | None:
    number = _number(value)
    return number if number and number > 0 else None


def parse_time(value: Any) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed.tzinfo is not None else None


def folder_url(slug: str | None) -> str | None:
    return f"{WEB_URL}/folders/{slug}" if slug else None


def normalize(text: str) -> str:
    return _OTHER.sub("", unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower())


@dataclass(frozen=True, slots=True)
class Store:
    store_id: str
    name: str
    slug: str | None
    logo: str | None

    @property
    def url(self) -> str | None:
        return f"{WEB_URL}/winkels/{self.slug}" if self.slug else None


@dataclass(frozen=True, slots=True)
class Folder:
    folder_id: str
    store_id: str
    name: str
    slug: str | None
    valid_from: datetime
    valid_until: datetime
    cover: str | None

    @property
    def url(self) -> str | None:
        return folder_url(self.slug)

    @property
    def image(self) -> str | None:
        return _THUMB.sub("", self.cover, count=1) if self.cover else None


@dataclass(frozen=True, slots=True)
class Offer:
    offer_id: str
    store_id: str
    title: str
    price: float | None
    sale_price: float | None
    page: int | None
    url: str | None
    valid_from: datetime
    valid_until: datetime
    word: str


@dataclass(frozen=True, slots=True)
class Shop:
    shop_id: str
    latitude: float
    longitude: float
    store_id: str
    street: str
    housenumber: str
    city: str

    @property
    def address(self) -> str:
        street = f"{self.street} {self.housenumber}".rstrip() if self.street else ""
        return ", ".join(part for part in (street, self.city) if part)


def _store(row: Mapping[str, Any]) -> Store | None:
    store_id, name = _match(_ID, row.get("id")), _text(row.get("name"))
    if store_id is None or not name:
        return None
    return Store(store_id, name, _match(_SLUG, row.get("slug")), _match(_IMAGE, row.get("logoUrl")))


def _folder(row: Mapping[str, Any]) -> Folder | None:
    folder_id, store_id = _match(_ID, row.get("id")), _match(_ID, _mapping(row.get("retailer")).get("id"))
    start, end = parse_time(row.get("validFrom")), parse_time(row.get("validUntil"))
    if folder_id is None or store_id is None or start is None or end is None:
        return None
    slug, cover = _match(_SLUG, row.get("slug")), _match(_IMAGE, row.get("coverUrl"))
    return Folder(folder_id, store_id, _text(row.get("name")), slug, start, end, cover)


def _offer(row: Mapping[str, Any], word: str) -> Offer | None:
    data, folder = _mapping(row.get("data")), _mapping(row.get("publicationVariant"))
    offer_id, store_id = _match(_ID, row.get("id")), _match(_ID, _mapping(row.get("retailer")).get("id"))
    start, end = parse_time(folder.get("validFrom")), parse_time(folder.get("validUntil"))
    title, page = _text(data.get("title")), row.get("publicationVariantPageIndex")
    if offer_id is None or store_id is None or start is None or end is None or not title:
        return None
    return Offer(
        offer_id,
        store_id,
        title,
        _price(data.get("price")),
        _price(data.get("priceSale")),
        page if isinstance(page, int) and not isinstance(page, bool) and page >= 0 else None,
        folder_url(_match(_SLUG, folder.get("slug"))),
        start,
        end,
        word,
    )


def _shop(element: Mapping[str, Any], index: Mapping[str, str]) -> Shop | None:
    tags, point = _mapping(element.get("tags")), _mapping(element.get("geometry")).get("coordinates")
    kind, number = tags.get("kind"), element.get("id")
    store_id = index.get(normalize(_text(tags.get("brand")))) or index.get(normalize(_text(tags.get("name"))))
    if (
        store_id is None
        or not isinstance(kind, str)
        or kind not in _KINDS
        or not isinstance(number, int)
        or isinstance(number, bool)
        or not 0 < number < 10**15
        or not isinstance(point, list)
        or len(point) != 2
    ):
        return None
    longitude, latitude = map(_number, point)
    if latitude is None or longitude is None or not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        return None
    address = (_text(tags.get(key)) for key in ("street", "housenumber", "city"))
    return Shop(f"{_KINDS[kind]}{number}", round(latitude, 5), round(longitude, 5), store_id, *address)


def store_index(stores: Collection[Store]) -> dict[str, str]:
    return {key: store.store_id for store in stores if len(key := normalize(store.name)) >= 2}


def overpass_query(stores: Collection[Store]) -> str:
    names = sorted({store.name for store in stores if len(normalize(store.name)) >= 2})
    return OVERPASS_QUERY.format(names="|".join(_SPECIAL.sub(r"\\\g<0>", name) for name in names))


async def _async_read(response: aiohttp.ClientResponse, limit: int) -> bytes:
    body = bytearray()
    async for chunk in response.content.iter_chunked(64 * 1024):
        body += chunk
        if len(body) > limit:
            raise FoldersError("The answer is too large")
    return bytes(body)


async def _async_request(
    session: aiohttp.ClientSession, method: str, url: str, wait: aiohttp.ClientTimeout, limit: int, **kwargs: Any
) -> tuple[int, bytes]:
    try:
        async with session.request(method, url, timeout=wait, allow_redirects=False, **kwargs) as response:
            if response.status != 200:
                return response.status, b""
            return 200, await _async_read(response, limit)
    except REQUEST_ERRORS as err:
        raise FoldersError(f"The request failed ({type(err).__name__})") from None


def _json(body: bytes) -> Mapping[str, Any]:
    try:
        return _mapping(json.loads(body))
    except (ValueError, RecursionError) as err:
        raise FoldersError(f"The request failed ({type(err).__name__})") from None


def image_type(data: bytes) -> str | None:
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return next((kind for magic, kind in IMAGE_MAGIC if data.startswith(magic)), None)


async def async_get_image(session: aiohttp.ClientSession, url: str, limit: int) -> tuple[str, bytes] | None:
    try:
        async with session.get(url, timeout=FOLDERS_TIMEOUT, allow_redirects=False) as response:
            data = await _async_read(response, limit) if response.status == 200 else b""
    except (*REQUEST_ERRORS, FoldersError):
        return None
    return (kind, data) if (kind := image_type(data)) else None


class FoldersClient:
    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session

    async def _async_items(self, kind: str, fields: str, pages: int, **options: Any) -> list[Mapping[str, Any]]:
        name = f"affiliateCms{kind}s"
        query = (
            f"query($o: InputAffiliateCms{kind}Pagination!){{ {name}(options:$o){{ meta{{ totalItems totalPages }} "
            f"items{{ {fields} }} }} }}"
        )
        items: list[Mapping[str, Any]] = []
        for page in range(1, pages + 1):
            variables = {"o": {"affiliateSlug": AFFILIATE, **options, "limit": PAGE_SIZE, "page": page}}
            params = {"query": query, "variables": json.dumps(variables, separators=(",", ":"))}
            status, body = await _async_request(
                self._session, "GET", GRAPHQL_URL, FOLDERS_TIMEOUT, FOLDERS_LIMIT, params=params
            )
            if status != 200:
                raise FoldersError(f"folders.nl answered HTTP {status}")
            data = _json(body)
            block = _mapping(_mapping(data.get("data")).get(name))
            if data.get("errors") or not isinstance(rows := block.get("items"), list):
                raise FoldersError("folders.nl sent an error or an unexpected answer")
            items.extend(row for row in rows if isinstance(row, Mapping))
            total = _mapping(block.get("meta")).get("totalPages")
            if not rows or not isinstance(total, int) or page >= total:
                break
        return items

    async def async_get_stores(self) -> dict[str, Store]:
        rows = await self._async_items("Retailer", "id name slug logoUrl", MAX_PAGES)
        if not (stores := {store.store_id: store for row in rows if (store := _store(row))}):
            raise FoldersError("folders.nl sent no stores")
        return stores

    async def async_get_folders(self) -> list[Folder]:
        fields = "id name slug validFrom validUntil coverUrl retailer{ id }"
        rows = await self._async_items("PublicationVariant", fields, MAX_PAGES, excludeExpired=True)
        return list({folder.folder_id: folder for row in rows if (folder := _folder(row))}.values())

    async def async_get_offers(self, word: str) -> list[Offer]:
        fields = "id data publicationVariantPageIndex retailer{ id } publicationVariant{ id slug validFrom validUntil }"
        rows = await self._async_items("PietTagging", fields, OFFER_PAGES, search=word)
        return [offer for row in rows if (offer := _offer(row, word))]


async def async_get_shops(session: aiohttp.ClientSession, stores: Collection[Store]) -> bytes:
    query = overpass_query(stores)
    request = partial(
        _async_request,
        session,
        "POST",
        OVERPASS_URL,
        OVERPASS_TIMEOUT,
        OVERPASS_LIMIT,
        data={"data": query},
        headers={"User-Agent": OVERPASS_AGENT},
    )
    status, body = await request()
    for delay in RETRY_DELAYS:
        if status not in RETRY_STATUSES:
            break
        await asyncio.sleep(delay)
        status, body = await request()
    if status != 200:
        raise FoldersError(f"OpenStreetMap answered HTTP {status}")
    return body


def parse_shops(body: bytes, stores: Collection[Store]) -> list[Shop]:
    data = _json(body)
    elements, remark = data.get("elements"), data.get("remark")
    if not isinstance(elements, list) or (
        isinstance(remark, str) and ("runtime error" in remark or "timed out" in remark)
    ):
        raise FoldersError("OpenStreetMap sent an error or an unexpected answer")
    index = store_index(stores)
    shops = (_shop(element, index) for element in elements if isinstance(element, Mapping))
    if not (found := list({shop.shop_id: shop for shop in shops if shop}.values())):
        raise FoldersError("OpenStreetMap sent no shops")
    return found
