from __future__ import annotations

import asyncio
from collections.abc import Collection, Iterable, Mapping
from dataclasses import dataclass, replace
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
FOLDER_PAGES = 400
HIT_PAGES = 20
HIT_LIMITS = (100, 25)
SUGGEST_ROWS = 30
OFFER_IMAGES = 5000
DISCOUNT = ({"property": "DISCOUNT_SCORE", "direction": "DESC"},)
RETRY_STATUSES = frozenset({429, 502, 503, 504})
RETRY_DELAYS = (30, 90)
TEXT_LIMIT = 200
CATEGORY_LIMIT = 60
STORE_FIELDS = "id name slug logoUrl website categories{ slug }"
FOLDER_FIELDS = "id name slug createdAt validFrom validUntil coverUrl retailer{ id } meta{ themes{ slug } }"
OFFER_FIELDS = (
    "id data publicationVariantPageIndex interactionImageUrl retailer{ id } "
    "publicationVariant{ id slug validFrom validUntil }"
)
DOCUMENT_FIELDS = "pietTaggingId data googleCategories"
FOLDER_QUERY = (
    "query($s: String!, $id: UUID!){ affiliateCmsPublicationVariant(affiliateSlug:$s, publicationVariantId:$id){ "
    "id thumbnailUrls } }"
)
FOLDER_OFFERS_QUERY = (
    "query($o: InputAffiliateCmsPublicationVariantPietTaggings!){ affiliateCmsPublicationVariantPietTaggings("
    "options:$o){ id data publicationVariantPageIndex interactionImageUrl } }"
)
SUGGEST_QUERY = (
    "query($o: InputAffiliateCmsPietTaggingPagination!){ affiliateCmsPietTaggings(options:$o){ items{ data "
    "publicationVariant{ id } } } }"
)
SEARCH_QUERY = (
    "query($o: InputAffiliateCmsSearchOptions!){ affiliateCmsSearch(options:$o){ publicationVariants{ page{ "
    "pageIndex } pages{ pageIndex } publicationVariant{ id } } retailers{ id } } }"
)
FEATURED_QUERY = (
    "query($s: String){ affiliateCmsPublicationVariantTopPositions(affiliateSlug:$s, onlyActive:true){ "
    "publicationVariant{ id } } }"
)
TEXT_QUERY = (
    "query($o: InputAffiliateCmsViewerOptions!){ affiliateCmsViewer(options:$o){ meta{ pages{ textContent } } } }"
)
OVERPASS_QUERY = (
    '[out:json][timeout:300];area["ISO3166-1"="NL"][admin_level=2]->.nl;nwr["shop"]["brand"~"^({names})$",i](area.nl);'
    'convert shop ::id=id(),::geom=center(geom()),kind=type(),brand=t["brand"],name=t["name"],street=t["addr:street"],'
    'housenumber=t["addr:housenumber"],city=t["addr:city"],opening_hours=t["opening_hours"];out geom;'
)
REQUEST_ERRORS = (aiohttp.ClientError, TimeoutError, ValueError)
UNEXPECTED = "folders.nl sent an error or an unexpected answer"
_ID = re.compile(r"[\w-]{1,64}", re.ASCII)
_SLUG = re.compile(r"[a-z0-9-]{1,120}")
_IMAGE = re.compile(r"https://(?:assets\.wepublish\.com|api\.wepublish\.digital)/[\w.~%/+=&?-]{1,2000}", re.ASCII)
_WEBSITE = re.compile(r"(?=.{1,200}\Z)https://[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*(?:/[\w.~%/+=&?-]*)?", re.ASCII)
_THUMB = re.compile(r"-thumb(?=\.\w+(?:\?|$))")
_PAGE = re.compile(r"pages%2F1-thumb\.jpg(?=\?|$)")
_SPECIAL = re.compile(r'[\\.^$|?*+()\[\]{}"]')
_SPACES = re.compile(r"[^a-z0-9]+")
_SEPARATORS = re.compile(r"[ :|/,;\u2013\u2014-]+")
_KINDS = {"node": "n", "way": "w", "relation": "r"}


class FoldersError(Exception):
    pass


class QueryError(FoldersError):
    pass


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _rows(value: Any) -> list[Mapping[str, Any]]:
    return [row for row in value if isinstance(row, Mapping)] if isinstance(value, list) else []


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


def _page(index: Any) -> int | None:
    return index + 1 if isinstance(index, int) and not isinstance(index, bool) and 0 <= index < FOLDER_PAGES else None


def _slugs(value: Any) -> tuple[str, ...]:
    return tuple(dict.fromkeys(slug for row in _rows(value) if (slug := _match(_SLUG, row.get("slug")))))


def parse_time(value: Any) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed.tzinfo is not None else None


def folder_url(slug: str | None) -> str | None:
    return f"{WEB_URL}/folders/{slug}" if slug else None


def plain(text: str) -> str:
    return _SPACES.sub(" ", unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()).strip()


def normalize(text: str) -> str:
    return plain(text).replace(" ", "")


def starts_with_store(name: str, store: str) -> bool:
    key = normalize(store)
    return bool(key) and (
        normalize(name) == key or any(normalize(name[: gap.start()]) == key for gap in _SEPARATORS.finditer(name))
    )


@dataclass(frozen=True, slots=True)
class Category:
    category_id: str
    name: str
    slug: str


@dataclass(frozen=True, slots=True)
class Store:
    store_id: str
    name: str
    slug: str | None
    logo: str | None
    categories: tuple[str, ...] = ()
    website: str | None = None

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
    created: datetime | None = None
    themes: tuple[str, ...] = ()

    @property
    def url(self) -> str | None:
        return folder_url(self.slug)

    @property
    def image(self) -> str | None:
        return _THUMB.sub("", self.cover, count=1) if self.cover else None

    def page(self, number: int, suffix: str = "") -> str | None:
        url, found = _PAGE.subn(f"pages%2F{number}{suffix}.jpg", self.cover or "", count=1)
        return url if found else None


@dataclass(frozen=True, slots=True)
class Offer:
    offer_id: str
    store_id: str
    folder_id: str
    title: str
    price: float | None
    sale_price: float | None
    page: int | None
    image: str | None
    url: str | None
    valid_from: datetime
    valid_until: datetime
    word: str = ""
    limit: float | None = None
    description: str | None = None
    product_category: str | None = None

    @property
    def ratio(self) -> float:
        return self.sale_price / self.price if self.price and self.sale_price else 1.0

    @property
    def identity(self) -> tuple[str, tuple[Any, ...]]:
        return self.offer_id, (self.store_id, self.title, self.price, self.sale_price, self.page)


@dataclass(frozen=True, slots=True)
class Found:
    offers: list[Offer]
    more: bool
    folders: dict[str, tuple[int, ...]] | None
    stores: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Shop:
    shop_id: str
    latitude: float
    longitude: float
    store_id: str
    street: str
    housenumber: str
    city: str
    hours: str = ""

    @property
    def address(self) -> str:
        street = f"{self.street} {self.housenumber}".rstrip() if self.street else ""
        return ", ".join(part for part in (street, self.city) if part)


def unique(offers: Iterable[Offer]) -> list[Offer]:
    seen: set[Any] = set()
    found: list[Offer] = []
    for offer in offers:
        if seen.isdisjoint(offer.identity):
            seen.update(offer.identity)
            found.append(offer)
    return found


def _category(row: Mapping[str, Any]) -> Category | None:
    category_id, name, slug = _match(_ID, row.get("id")), _text(row.get("name")), _match(_SLUG, row.get("slug"))
    return Category(category_id, name, slug) if category_id and name and slug else None


def _store(row: Mapping[str, Any]) -> Store | None:
    store_id, name = _match(_ID, row.get("id")), _text(row.get("name"))
    if store_id is None or not name:
        return None
    slug, logo, website = (
        _match(pattern, row.get(key)) for pattern, key in ((_SLUG, "slug"), (_IMAGE, "logoUrl"), (_WEBSITE, "website"))
    )
    return Store(store_id, name, slug, logo, _slugs(row.get("categories")), website)


def _folder(row: Mapping[str, Any]) -> Folder | None:
    folder_id, store_id = _match(_ID, row.get("id")), _match(_ID, _mapping(row.get("retailer")).get("id"))
    start, end = parse_time(row.get("validFrom")), parse_time(row.get("validUntil"))
    if folder_id is None or store_id is None or start is None or end is None or end < start:
        return None
    return Folder(
        folder_id,
        store_id,
        _text(row.get("name")),
        _match(_SLUG, row.get("slug")),
        start,
        end,
        _match(_IMAGE, row.get("coverUrl")),
        parse_time(row.get("createdAt")),
        _slugs(_mapping(row.get("meta")).get("themes")),
    )


def _offer(row: Mapping[str, Any], folder: Folder | None) -> Offer | None:
    data, variant = _mapping(row.get("data")), _mapping(row.get("publicationVariant"))
    if folder is None:
        store_id, folder_id = _match(_ID, _mapping(row.get("retailer")).get("id")), _match(_ID, variant.get("id"))
        start, end = parse_time(variant.get("validFrom")), parse_time(variant.get("validUntil"))
        url = folder_url(_match(_SLUG, variant.get("slug")))
    else:
        store_id, folder_id, start, end, url = (
            folder.store_id,
            folder.folder_id,
            folder.valid_from,
            folder.valid_until,
            folder.url,
        )
    offer_id, title = _match(_ID, row.get("id")), _text(data.get("title"))
    if offer_id is None or store_id is None or folder_id is None or start is None or end is None or not title:
        return None
    return Offer(
        offer_id,
        store_id,
        folder_id,
        title,
        _price(data.get("price")),
        _price(data.get("priceSale")),
        _page(row.get("publicationVariantPageIndex")),
        _match(_IMAGE, row.get("interactionImageUrl")),
        url,
        start,
        end,
    )


def _details(row: Mapping[str, Any]) -> dict[str, str | None]:
    description, paths = _text(_mapping(row.get("data")).get("description")), row.get("googleCategories")
    category = _text(paths[0])[:CATEGORY_LIMIT].rstrip() if isinstance(paths, list) and paths else ""
    return {"description": None if description in ("", "-") else description, "product_category": category or None}


def _hits(block: Mapping[str, Any]) -> tuple[dict[str, tuple[int, ...]], tuple[str, ...]]:
    folders: dict[str, set[int]] = {}
    for hit in _rows(block.get("publicationVariants")):
        pages = {
            number
            for row in (hit.get("page"), *_rows(hit.get("pages")))
            if (number := _page(_mapping(row).get("pageIndex")))
        }
        if pages and (folder_id := _match(_ID, _mapping(hit.get("publicationVariant")).get("id"))):
            folders.setdefault(folder_id, set()).update(pages)
    stores = dict.fromkeys(
        store_id for row in _rows(block.get("retailers")) if (store_id := _match(_ID, row.get("id")))
    )
    return {folder_id: tuple(sorted(pages))[:HIT_PAGES] for folder_id, pages in folders.items()}, tuple(stores)


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
    details = (_text(tags.get(key)) for key in ("street", "housenumber", "city", "opening_hours"))
    return Shop(f"{_KINDS[kind]}{number}", round(latitude, 5), round(longitude, 5), store_id, *details)


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
        self.images: dict[str, str] = {}

    async def _async_data(
        self, query: str, variables: Mapping[str, Any], name: str, kind: type | tuple[type, ...] = Mapping
    ) -> Any:
        params = {"query": query, "variables": json.dumps(variables, separators=(",", ":"))}
        status, body = await _async_request(
            self._session, "GET", GRAPHQL_URL, FOLDERS_TIMEOUT, FOLDERS_LIMIT, params=params
        )
        if status != 200:
            raise FoldersError(f"folders.nl answered HTTP {status}")
        data = _json(body)
        if data.get("errors"):
            raise QueryError(UNEXPECTED)
        if not isinstance(block := _mapping(data.get("data")).get(name), kind):
            raise FoldersError(UNEXPECTED)
        return block

    async def _async_page(
        self, name: str, kind: str, fields: str, page: int, limit: int = PAGE_SIZE, **options: Any
    ) -> tuple[list[Mapping[str, Any]], bool]:
        query = (
            f"query($o: InputAffiliateCms{kind}Pagination!){{ {name}(options:$o){{ meta{{ totalItems totalPages }} "
            f"items{{ {fields} }} }} }}"
        )
        variables = {"o": {"affiliateSlug": AFFILIATE, **options, "limit": limit, "page": page}}
        block = await self._async_data(query, variables, name)
        if not isinstance(rows := block.get("items"), list):
            raise FoldersError(UNEXPECTED)
        total = _mapping(block.get("meta")).get("totalPages")
        return _rows(rows), bool(rows) and isinstance(total, int) and page < total

    async def _async_items(self, name: str, kind: str, fields: str, **options: Any) -> list[Mapping[str, Any]]:
        items: list[Mapping[str, Any]] = []
        for page in range(1, MAX_PAGES + 1):
            rows, more = await self._async_page(name, kind, fields, page, **options)
            items += rows
            if not more:
                break
        return items

    async def _async_details(self, page: int, **options: Any) -> tuple[dict[str, dict[str, str | None]], bool]:
        try:
            rows, more = await self._async_page(
                "affiliateCmsPietTaggingDocuments", "PietTagging", DOCUMENT_FIELDS, page, **options
            )
        except FoldersError:
            return {}, True
        return {offer_id: _details(row) for row in rows if (offer_id := _match(_ID, row.get("pietTaggingId")))}, more

    async def _async_hits(self, text: str) -> tuple[dict[str, tuple[int, ...]] | None, tuple[str, ...]]:
        for limit in HIT_LIMITS:
            variables = {"o": {"affiliateSlug": AFFILIATE, "query": text, "limit": limit}}
            try:
                return _hits(await self._async_data(SEARCH_QUERY, variables, "affiliateCmsSearch"))
            except QueryError:
                continue
            except FoldersError:
                break
        return None, ()

    def keep(self, offers: Iterable[Offer]) -> None:
        for offer in offers:
            if offer.image:
                self.images.pop(offer.offer_id, None)
                self.images[offer.offer_id] = offer.image
        while len(self.images) > OFFER_IMAGES:
            del self.images[next(iter(self.images))]

    def _offers(
        self, rows: Iterable[Mapping[str, Any]], details: Mapping[str, Mapping[str, Any]], folder: Folder | None = None
    ) -> list[Offer]:
        offers = [replace(offer, **details.get(offer.offer_id, {})) for row in rows if (offer := _offer(row, folder))]
        self.keep(offers)
        return offers

    async def _async_labels(self, name: str, kind: str) -> dict[str, Category]:
        rows = await self._async_items(name, kind, "id name slug")
        return {category.slug: category for row in rows if (category := _category(row))}

    async def async_get_stores(self) -> dict[str, Store]:
        rows = await self._async_items("affiliateCmsRetailers", "Retailer", STORE_FIELDS)
        if not (stores := {store.store_id: store for row in rows if (store := _store(row))}):
            raise FoldersError("folders.nl sent no stores")
        return stores

    async def async_get_categories(self) -> dict[str, Category]:
        return await self._async_labels("affiliateCmsCategories", "Category")

    async def async_get_themes(self) -> dict[str, Category]:
        return await self._async_labels("affiliateCmsThemes", "Theme")

    async def async_get_folders(self) -> list[Folder]:
        rows = await self._async_items(
            "affiliateCmsPublicationVariants", "PublicationVariant", FOLDER_FIELDS, excludeExpired=True
        )
        return list({folder.folder_id: folder for row in rows if (folder := _folder(row))}.values())

    async def async_get_featured(self) -> frozenset[str]:
        rows = await self._async_data(
            FEATURED_QUERY, {"s": AFFILIATE}, "affiliateCmsPublicationVariantTopPositions", list
        )
        variants = (_mapping(row.get("publicationVariant")).get("id") for row in _rows(rows))
        return frozenset(folder_id for folder_id in variants if _match(_ID, folder_id))

    async def async_search(self, text: str) -> Found:
        offers: list[Offer] = []
        for page in range(1, OFFER_PAGES + 1):
            rows, more = await self._async_page(
                "affiliateCmsPietTaggings", "PietTagging", OFFER_FIELDS, page, search=text
            )
            offers += self._offers(rows, (await self._async_details(page, search=text))[0])
            if not more:
                break
        return Found(offers, more, *await self._async_hits(text))

    async def async_suggest(self, text: str) -> list[tuple[str, str]]:
        variables = {"o": {"affiliateSlug": AFFILIATE, "search": text, "limit": SUGGEST_ROWS, "page": 1}}
        block = await self._async_data(SUGGEST_QUERY, variables, "affiliateCmsPietTaggings")
        if not isinstance(rows := block.get("items"), list):
            raise FoldersError(UNEXPECTED)
        key = normalize(text)
        return [
            (title, folder_id)
            for row in _rows(rows)
            if key in normalize(title := _text(_mapping(row.get("data")).get("title")))
            and (folder_id := _match(_ID, _mapping(row.get("publicationVariant")).get("id")))
        ]

    async def async_get_deals(self, limit: int, **options: str) -> list[Offer]:
        rows, _ = await self._async_page(
            "affiliateCmsPietTaggings", "PietTagging", OFFER_FIELDS, 1, limit, orderBy=DISCOUNT, **options
        )
        return self._offers(rows, {})

    async def async_get_folder(self, folder: Folder) -> tuple[int, list[Offer]]:
        block = await self._async_data(
            FOLDER_QUERY, {"s": AFFILIATE, "id": folder.folder_id}, "affiliateCmsPublicationVariant"
        )
        if not isinstance(pages := block.get("thumbnailUrls"), list) or not pages:
            raise FoldersError(UNEXPECTED)
        rows = _rows(
            await self._async_data(
                FOLDER_OFFERS_QUERY,
                {"o": {"affiliateSlug": AFFILIATE, "publicationVariantId": folder.folder_id}},
                "affiliateCmsPublicationVariantPietTaggings",
                list,
            )
        )
        details: dict[str, dict[str, str | None]] = {}
        page, more = 0, bool(rows)
        while more and page < OFFER_PAGES:
            page += 1
            found, more = await self._async_details(page, publicationVariantId=folder.folder_id)
            details |= found
        return min(len(pages), FOLDER_PAGES), self._offers(rows, details, folder)

    async def async_get_text(self, folder: Folder) -> tuple[str, ...]:
        block = await self._async_data(
            TEXT_QUERY,
            {"o": {"affiliateSlug": AFFILIATE, "slug": folder.slug}},
            "affiliateCmsViewer",
            (Mapping, type(None)),
        )
        if block is None:
            return ()
        if not isinstance(pages := _mapping(block.get("meta")).get("pages"), list):
            raise FoldersError(UNEXPECTED)
        texts = (_mapping(page).get("textContent") for page in pages[:FOLDER_PAGES])
        return tuple(text if isinstance(text, str) else "" for text in texts)


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
