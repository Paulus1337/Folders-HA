const STYLE = `
:host { display: block; height: 100%; }
ha-card { height: 100%; box-sizing: border-box; overflow: auto; overflow-wrap: anywhere; }
ha-card.maps { display: flex; flex-direction: column; overflow: hidden; }
:host([ispanel]) { display: grid; min-height: 50vh; }
:host([ispanel]) ha-card.maps { contain: size; }
[hidden] { display: none !important; }
button { padding: 0; border: 0; background: none; color: inherit; font: inherit; text-align: left; cursor: pointer; }
button:disabled { opacity: 0.4; cursor: default; }
img { display: block; max-width: 100%; }
.top { display: grid; grid-template-columns: minmax(0, 1fr); gap: 8px; padding: 16px 16px 0; }
.search, .head, .controls, .bar, .links, .found { display: flex; align-items: center; gap: 12px; }
.controls, .links, .found { flex-wrap: wrap; }
input[type="search"] {
  flex: 1; min-width: 0; padding: 8px 12px; border: 1px solid var(--divider-color); border-radius: 18px;
  background: var(--card-background-color); color: var(--primary-text-color); font: inherit;
}
.field { position: relative; display: flex; flex: 1; min-width: 0; }
.tips {
  position: absolute; top: 100%; left: 0; right: 0; z-index: 1001; max-height: 50vh; overflow-y: auto; margin-top: 4px;
  padding: 4px 0; border: 1px solid var(--divider-color); border-radius: 12px; background: var(--card-background-color);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.25);
}
.maps .tips { max-height: min(50vh, 400px); }
.tip { display: flex; align-items: center; gap: 12px; padding: 8px 12px; cursor: pointer; }
.tip:hover, .tip[aria-selected="true"] { background: var(--secondary-background-color); }
.tip img { height: 24px; max-width: 48px; object-fit: contain; }
.tip ha-icon { --mdc-icon-size: 20px; color: var(--secondary-text-color); }
.go { padding: 8px 16px; border-radius: 18px; background: var(--primary-color); color: var(--text-primary-color); }
.toggle { display: flex; align-items: center; gap: 6px; font-size: 0.9em; white-space: nowrap; }
.chips { display: flex; gap: 8px; padding: 12px 16px 0; overflow-x: auto; scrollbar-width: thin; }
.line { flex: none; padding: 8px 16px; }
.results { padding-top: 12px; }
.results .head, .panel .head { justify-content: space-between; }
.chip, .step { flex: none; padding: 4px 12px; border: 1px solid var(--divider-color); border-radius: 16px; }
.chip { display: flex; align-items: center; gap: 6px; }
.chip ha-icon { --mdc-icon-size: 18px; }
.chip img { height: 20px; max-width: 48px; object-fit: contain; }
.chip[aria-pressed="true"] {
  border-color: var(--primary-color); background: var(--primary-color); color: var(--text-primary-color);
}
.step, .add, .more, .link, .open, .actions button { color: var(--primary-color); }
.add, .more, .link, .open { font-size: 0.9em; }
.heading { padding: 16px 16px 0; font-weight: 500; }
.pad { padding: 0 16px; }
.deals {
  display: grid; grid-auto-flow: column; grid-auto-columns: 140px; gap: 12px; padding: 8px 16px 4px; overflow-x: auto;
  scrollbar-width: thin;
}
.items { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 12px; padding: 8px 16px 0; }
.item, .show, .cell, .others, .thumb { display: grid; gap: 4px; align-content: start; }
.item img, .tile img, .shop img, .row img, .thumb img {
  width: 100%; aspect-ratio: 1; object-fit: contain; border-radius: 8px; background: var(--secondary-background-color);
}
.tile img, .shop img, .row img, .thumb img { aspect-ratio: 3 / 4; object-fit: cover; }
.near img { aspect-ratio: 1; object-fit: contain; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 12px; padding: 16px; }
.tile { position: relative; display: grid; gap: 2px; align-content: start; }
.hits { display: grid; gap: 12px; padding: 8px 16px 0; }
.row, .shop { display: grid; grid-template-columns: 64px minmax(0, 1fr); gap: 12px; align-items: start; }
.shop { grid-template-columns: 96px minmax(0, 1fr); }
.near { grid-template-columns: 40px minmax(0, 1fr); }
.sheet { display: grid; grid-template-columns: repeat(auto-fill, minmax(88px, 1fr)); gap: 8px; }
.thumb[aria-current="page"] img { outline: 3px solid var(--primary-color); outline-offset: -3px; }
.badge {
  position: absolute; top: 6px; left: 6px; padding: 2px 8px; border-radius: 10px;
  background: var(--primary-color); color: var(--text-primary-color); font-size: 0.8em;
}
.name { font-weight: 500; }
.small { color: var(--secondary-text-color); font-size: 0.9em; }
.text { padding: 16px; }
.body { position: relative; flex: 1; display: flex; flex-direction: column; min-height: 0; }
.map { position: relative; flex: 1 1 300px; min-height: 35%; }
ha-map { position: absolute; inset: 0; height: auto; z-index: 0; }
.hint {
  position: absolute; top: 8px; left: 50%; transform: translateX(-50%); z-index: 1000; padding: 4px 12px;
  border-radius: 16px; background: var(--card-background-color); pointer-events: none;
}
.bar { flex: none; box-sizing: border-box; height: 48px; padding: 0 16px; }
.bar .chips { flex: 1; padding: 0; }
.set { display: flex; flex: none; gap: 8px; }
.panel {
  display: grid; gap: 12px; flex: 0 1 auto; min-height: 0; max-height: 50%; overflow: auto;
  padding: 12px 16px; border-top: 1px solid var(--divider-color);
}
.panel .items { padding: 0; }
.actions { display: flex; gap: 16px; margin-top: 8px; }
.footer { padding: 4px 16px 8px; color: var(--secondary-text-color); font-size: 0.8em; }
.viewer { padding: 8px 16px 16px; outline: none; }
.viewer > * + *, .frame > * + * { margin-top: 8px; }
.viewer .heading, .viewer .items, .viewer .text { padding-left: 0; padding-right: 0; }
.over { position: absolute; inset: 0; z-index: 1001; overflow: auto; background: var(--card-background-color); }
.page { overflow: auto; touch-action: pan-y pinch-zoom; }
.page img { width: 100%; max-width: 720px; height: auto; margin: 0 auto; user-select: none; }
.zoomed { touch-action: pan-x pan-y pinch-zoom; }
.zoomed img { width: 200%; max-width: 1440px; }
`;
const TEXTS = {
  en: {
    until: "until",
    from: "from",
    more: "more",
    was: "was",
    new: "New",
    search: "Search offers",
    find: "Search",
    tips: "Suggestions",
    watch: "Watch",
    mine: "Only my stores",
    area: "Near you",
    you: "Around your location",
    home: "Around home",
    short: "Type 2 to 40 characters.",
    busy: "Searching",
    nothing: "No offers found.",
    many: "More offers found, search more precisely to see them.",
    cannot: "Searching is not possible right now.",
    nearest: "Nearest first",
    found: "Found in folders",
    deals: "Best deals",
    list: "Watch list",
    quiet: "No offers right now.",
    mentioned: "Mentioned in",
    featured: "Featured",
    other: "Other",
    empty:
      "No folders right now. Check which stores and categories you left out in Settings > Devices & services > " +
      "Folders > Configure.",
    down: "The folders are not available right now.",
    add: "Add to shopping list",
    added: "Added to the shopping list",
    watched: "Added to the watch list",
    lost: "That did not work. Try again later.",
    back: "Back",
    previous: "Previous",
    next: "Next",
    page: "Page",
    pages: "Pages",
    of: "of",
    zoomIn: "Zoom in",
    zoomOut: "Zoom out",
    thumbs: "All pages",
    look: "Search in this folder",
    p: "p.",
    missed: "No matches in this folder.",
    blind: "Searching in this folder is not possible right now.",
    here: "On this page",
    site: "Open on folders.nl",
    website: "Website",
    wait: "Loading the folder",
    gone: "This folder is no longer available.",
    broken: "The folder could not be loaded right now.",
    hours: "Opening hours",
    zoom: "Zoom in to see the shops",
    loading: "Loading the shops of the Netherlands, this takes a few minutes",
    unavailable: "Shops are not available right now",
    all: "Zoom in to see all shops",
    near: "Nearest shops with",
    far: "No shops found for these offers.",
    failed: "The map could not be loaded.",
    open: "Open folder",
    close: "Close",
    footer: "Shops (c) OpenStreetMap contributors, folders from folders.nl",
  },
  nl: {
    until: "t/m",
    from: "vanaf",
    more: "meer",
    was: "was",
    new: "Nieuw",
    search: "Zoek aanbiedingen",
    find: "Zoeken",
    tips: "Suggesties",
    watch: "Volgen",
    mine: "Alleen mijn winkels",
    area: "In de buurt",
    you: "Rond je locatie",
    home: "Rond thuis",
    short: "Typ 2 tot 40 tekens.",
    busy: "Bezig met zoeken",
    nothing: "Geen aanbiedingen gevonden.",
    many: "Er zijn meer aanbiedingen, zoek preciezer om ze te zien.",
    cannot: "Zoeken lukt nu niet.",
    nearest: "Dichtstbij eerst",
    found: "Gevonden in folders",
    deals: "Beste aanbiedingen",
    list: "Volglijst",
    quiet: "Nu geen aanbiedingen.",
    mentioned: "Genoemd in",
    featured: "Uitgelicht",
    other: "Overig",
    empty:
      "Er zijn nu geen folders. Kijk welke winkels en categorieen je hebt uitgesloten via Instellingen > " +
      "Apparaten & diensten > Folders > Configureren.",
    down: "De folders zijn nu niet beschikbaar.",
    add: "Op boodschappenlijst",
    added: "Op de boodschappenlijst gezet",
    watched: "Toegevoegd aan de volglijst",
    lost: "Dat lukte niet. Probeer het later opnieuw.",
    back: "Terug",
    previous: "Vorige",
    next: "Volgende",
    page: "Pagina",
    pages: "Pagina's",
    of: "van",
    zoomIn: "Inzoomen",
    zoomOut: "Uitzoomen",
    thumbs: "Alle pagina's",
    look: "Zoek in deze folder",
    p: "p.",
    missed: "Niet gevonden in deze folder.",
    blind: "Zoeken in deze folder lukt nu niet.",
    here: "Op deze pagina",
    site: "Openen op folders.nl",
    website: "Website",
    wait: "De folder wordt geladen",
    gone: "Deze folder is niet meer beschikbaar.",
    broken: "De folder kan nu niet worden geladen.",
    hours: "Openingstijden",
    zoom: "Zoom in om de winkels te zien",
    loading: "De winkels van Nederland worden geladen, dit duurt een paar minuten",
    unavailable: "De winkels zijn nu niet beschikbaar",
    all: "Zoom in om alle winkels te zien",
    near: "Dichtstbijzijnde winkels met",
    far: "Geen winkels gevonden voor deze aanbiedingen.",
    failed: "De kaart kon niet worden geladen.",
    open: "Folder openen",
    close: "Sluiten",
    footer: "Winkels (c) OpenStreetMap-bijdragers, folders van folders.nl",
  },
};
const KIND_ICONS = {
  "auto-en-vervoer": "car", "baby-en-kind": "baby-carriage", bouwmarkt: "hammer-wrench", dieren: "paw",
  drogisterij: "pill", elektronica: "television", mode: "tshirt-crew", slijterij: "glass-wine",
  "speelgoed-en-spel": "puzzle", supermarkt: "cart", tuinieren: "flower", vakantie: "beach", "vrije-tijd": "bike",
  warenhuis: "store", weekenddeals: "calendar-weekend", wonen: "sofa", other: "dots-horizontal",
};
const THEME_ICONS = {
  "black-friday": "tag", herfst: "leaf-maple", vakantie: "airplane", sinterklaas: "gift", kerst: "pine-tree",
  duitsland: "flag",
};
const SITE = "https://folders.nl/";
const WEB = /^https:\/\/[a-z0-9.-]+(\/[^\s"'<>\\]*)?$/i;
const SIGNED = /^\/api\/folders\/image\/\w+\/[\w-][\w.-]*\?authSig=[\w.-]+$/;
const HALF_HOUR = 1800000;
const UUID = /^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$/i;
const SLUG = /^[a-z0-9-]{1,120}$/;
const LIMIT = /\s*(<|(^|\s)(max|under|onder)(?=\s*\u20ac?\s*\d))\s*\u20ac?\s*[\d.,]*$/i;
const POINTER = "ha-entity-marker { cursor: pointer; }";
const FEATURED = "*";

const el = (tag, props, ...children) => {
  const node = Object.assign(document.createElement(tag), props);
  node.append(...children.filter(Boolean));
  return node;
};
const fill = (node, ...children) => node.replaceChildren(...children.filter(Boolean));
const text = (value) => (typeof value === "string" ? value : "");
const line = (className, value) => value && el("div", { className, textContent: value });
const button = (className, label, onclick) => el("button", { type: "button", className, textContent: label, onclick });
const link = (label, url) => button("link", label, () => window.open(url, "_blank", "noopener,noreferrer"));
const list = (value) => (Array.isArray(value) ? value.filter((item) => item && typeof item === "object") : []);
const uuid = (value) => (typeof value === "string" && UUID.test(value) ? value : null);
const clean = (value) => text(value).trim().replace(/\s+/g, " ");
const bare = (value) => clean(value).replace(LIMIT, "");
const fits = (query) => query.length >= 2 && query.length <= 40;
const apart = (a, b) => {
  const rad = Math.PI / 180;
  const lat = Math.sin(((b.lat - a.lat) * rad) / 2) ** 2;
  const lon = Math.sin(((b.lon - a.lon) * rad) / 2) ** 2;
  return 12742 * Math.asin(Math.sqrt(lat + Math.cos(a.lat * rad) * Math.cos(b.lat * rad) * lon));
};
const shorten = (value) => {
  const cut = value.slice(0, 41).replace(/\s*\S*$/, "");
  return value.length <= 40 ? value : fits(cut) ? cut : value.slice(0, 40);
};
const numbers = (value) => (Array.isArray(value) ? value.filter((page) => Number.isInteger(page) && page > 0) : []);
const icon = (icons, slug, fallback) => `mdi:${Object.hasOwn(icons, slug) ? icons[slug] : fallback}`;
const kinds = (value) => {
  const slugs = (Array.isArray(value) ? value : []).filter((slug) => SLUG.test(text(slug)));
  return slugs.length ? slugs : ["other"];
};
const day = (hass, language, value, shift = 0) => {
  const time = Date.parse(value);
  if (!Number.isFinite(time)) return "";
  const timeZone = hass?.locale?.time_zone === "server" ? hass.config?.time_zone : undefined;
  try {
    const format = new Intl.DateTimeFormat(language, { weekday: "short", day: "numeric", month: "short", timeZone });
    return format.format(new Date(time - shift));
  } catch {
    return "";
  }
};
const period = (hass, language, t, from, until) => {
  const later = Date.parse(from) > Date.now();
  const shown = later ? day(hass, language, from) : day(hass, language, until, 1000);
  return shown && `${later ? t.from : t.until} ${shown}`;
};
const money = (language, value) =>
  typeof value === "number" && value > 0 && Number.isFinite(value)
    ? new Intl.NumberFormat(language, { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(value)
    : "";
const price = (t, language, item) => {
  const sale = money(language, item.sale_price);
  const full = money(language, item.price);
  return sale && full && sale !== full ? `${sale} (${t.was} ${full})` : sale || full;
};
const far = (language, item) => {
  const known = Number.isFinite(item.distance) && item.distance >= 0;
  const km = new Intl.NumberFormat(language, { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  return [known && `${km.format(item.distance)} km`, text(item.address)].filter(Boolean).join(", ");
};
const where = (t, pages) => {
  if (pages.length < 2) return pages.length ? `${t.page} ${pages[0]}` : "";
  return `${t.pages} ${pages.slice(0, 3).join(", ")}${pages.length > 3 ? ` +${pages.length - 3}` : ""}`;
};
const shortName = (folder, store) => {
  const fold = (value) =>
    value.normalize("NFKD").replace(/[^\x00-\x7f]/g, "").toLowerCase().replace(/[^a-z0-9]/g, "");
  const upper = (_, open, first) => open + first.toUpperCase();
  const name = text(folder);
  const key = fold(text(store));
  for (const gap of key ? name.matchAll(/[ :|\/,;\u2013\u2014-]+/g) : []) {
    const rest = name.slice(gap.index + gap[0].length);
    if (rest && fold(name.slice(0, gap.index)) === key) return rest.replace(/^([(\[{"]*)(ij|.)/iu, upper);
  }
  return name;
};

class FoldersCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._paths = new Map();
    this._consumers = new Map();
    this._off = new Set();
    this._gone = new Set();
    this._wide = new Set();
  }

  setConfig(config) {
    const view = config?.view ?? "folders";
    const zoom = config?.zoom ?? 14;
    const radius = config?.radius ?? 5;
    const shopping = config?.shopping_list ?? "todo.shopping_list";
    if (view !== "folders" && view !== "map") throw new Error("view must be folders or map");
    if (typeof zoom !== "number" || !(zoom >= 1 && zoom <= 20)) throw new Error("zoom must be a number from 1 to 20");
    if (typeof radius !== "number" || !(radius >= 0.5 && radius <= 50)) {
      throw new Error("radius must be a number from 0.5 to 50");
    }
    if (typeof shopping !== "string" || !/^todo\.[a-z0-9_]+$/.test(shopping)) {
      throw new Error("shopping_list must be a todo entity");
    }
    this._stop();
    this._config = { view, zoom, radius, list: shopping };
    this._map = this._drawn = this._look = this._marks = this._data = this._found = this._viewer = undefined;
    this._card = this._main = this._rest = this._body = this._hunt = this._spot = this._tips = undefined;
    this._shops = {};
    this._raw = [[], {}];
    this.shadowRoot.replaceChildren();
    this._start();
    if (this._hass) this.hass = this._hass;
  }

  getCardSize() {
    return this._config?.view === "map" ? 10 : (this._size ?? 6);
  }

  getGridOptions() {
    return this._config?.view === "map" ? { columns: "full", rows: 10, min_rows: 10 } : { columns: "full" };
  }

  static getStubConfig() {
    return {};
  }

  connectedCallback() {
    this._link();
    this._start();
    this._pend();
  }

  disconnectedCallback() {
    this._stop();
  }

  set layout(value) {
    this.toggleAttribute("ispanel", value === "panel");
  }

  set isPanel(value) {
    this.toggleAttribute("ispanel", value === true);
  }

  set hass(hass) {
    const old = this._hass;
    this._hass = hass;
    this._list = this._config && hass.states[this._config.list] ? this._config.list : undefined;
    if (this._config?.view === "folders") {
      this._watch(hass);
      this._track();
    } else if (this._map && (!old || ["themes", "language", "locale"].some((key) => old[key] !== hass[key]))) {
      this._sync();
      this._bar();
      this._drawHunt();
    }
    this._start();
    this._pend();
  }

  _texts() {
    const language = this._hass?.locale?.language || this._hass?.language || "en";
    return { language, t: TEXTS[/^nl/i.test(language) ? "nl" : "en"] };
  }

  _watch(hass) {
    if (hass.entities !== this._registry) {
      this._registry = hass.entities;
      this._ids = Object.values(hass.entities || {})
        .filter((entry) => entry?.platform === "folders" && /^(calendar|event|sensor|todo)\./.test(entry.entity_id))
        .map((entry) => entry.entity_id);
    }
    const ids = this._ids.filter((id) => hass.states[id]);
    const watch = ids.find((id) => id.startsWith("todo."));
    const look = [this._texts().language, watch, this._list].join();
    if (look !== this._look) {
      this._look = look;
      this._watchList = watch;
      this._layout();
    }
    const marks = ids.map((id) => hass.states[id]);
    const changed = marks.length !== this._marks?.length || marks.some((mark, index) => mark !== this._marks[index]);
    if (this._marks && changed && this.isConnected) {
      clearTimeout(this._soon);
      this._soon = setTimeout(() => this._refresh(), 2000);
    }
    this._marks = marks;
  }

  _layout() {
    const { language, t } = this._texts();
    const input = el("input", {
      type: "search",
      value: this._input?.value || "",
      placeholder: t.search,
      ariaLabel: t.search,
      maxLength: 40,
      enterKeyHint: "search",
    });
    const scope = el("input", {
      type: "checkbox",
      checked: this._scope === true,
      onchange: () => {
        this._scope = scope.checked;
        if (this._found) this._search(this._found.query);
      },
    });
    this._input = input;
    this._results = el("div", { className: "results", hidden: true });
    this._pickRow = el("div", { className: "chips" });
    this._shown = el("div", { className: "items" });
    this._themeRow = el("div", { className: "chips" });
    this._kindRow = el("div", { className: "set" });
    this._nearChip = el(
      "button",
      { type: "button", className: "chip", onclick: () => void this._nearby() },
      el("ha-icon", { icon: "mdi:map-marker-radius" }),
      `${t.area}, ${new Intl.NumberFormat(language).format(this._config.radius)} km`,
    );
    this._rest = el("div");
    const search = el(
      "div",
      { className: "search" },
      this._field(input, (value) => this._search(value)),
      button("go", t.find, () => this._search(input.value)),
      this._watchList && button("go", t.watch, () => this._follow(input.value)),
    );
    const top = el("div", { className: "top" }, search, el("label", { className: "toggle" }, scope, t.mine));
    const kinds = el("div", { className: "chips" }, this._nearChip, this._kindRow);
    this._main = el("div", {}, top, this._results, this._themeRow, kinds, this._rest);
    this._card = el("ha-card", {}, this._main);
    this.shadowRoot.replaceChildren(el("style", { textContent: STYLE }), this._card);
    this._draw();
    this._drawFound();
    if (this._viewer) {
      this._main.hidden = true;
      this._card.append(this._viewer.root);
    }
  }

  _field(input, run) {
    const box = el("div", {
      className: "tips",
      id: "tips",
      role: "listbox",
      ariaLabel: this._texts().t.tips,
      hidden: true,
      onmousedown: (ev) => {
        ev.preventDefault();
      },
    });
    input.setAttribute("aria-controls", box.id);
    input.addEventListener("compositionend", () => this._typed());
    Object.assign(input, {
      role: "combobox",
      autocomplete: "off",
      ariaAutoComplete: "list",
      ariaExpanded: "false",
      oninput: (ev) => {
        if (ev.isComposing) clearTimeout(this._wait);
        else this._typed();
      },
      onkeydown: (ev) => {
        this._press(ev);
      },
      onblur: () => {
        clearTimeout(this._wait);
        if (this.isConnected) this._wait = setTimeout(() => this._close(), 200);
      },
    });
    this._tips = { input, box, run, rows: [], active: -1 };
    return el("div", { className: "field" }, input, box);
  }

  _typed() {
    const query = bare(this._tips.input.value);
    clearTimeout(this._wait);
    if (!fits(query)) this._close();
    else {
      this._mark(-1);
      this._wait = setTimeout(() => this._suggest(query), 300);
    }
  }

  async _suggest(query) {
    if (this._asking) {
      this._next = query;
      return;
    }
    const tips = this._tips;
    const asked = (this._tipped = (this._tipped || 0) + 1);
    let answer = null;
    this._asking = true;
    try {
      answer = await this._hass.callWS({ type: "folders/suggest", query });
    } catch {
      answer = null;
    }
    const next = this._next;
    const now = bare(this._tips?.input.value);
    this._asking = this._next = undefined;
    if (asked !== this._tipped || tips !== this._tips || now !== query) {
      if (next === now) this._suggest(next);
      return;
    }
    const at = Date.now();
    const ok = answer?.status === "ok";
    const stores = list(ok && answer.stores).filter((store) => uuid(store.folder_id) && clean(store.name));
    const titles = list(ok && answer.products).map((item) => clean(item.title)).filter(Boolean);
    this._offer([
      ...stores.map((store) => {
        const logo = this._keep(store.logo, at);
        const pick = () => {
          this._close();
          this._read(store.folder_id, 1, tips.input);
        };
        return [pick, logo && el("img", { src: logo, alt: "" }), text(store.name)];
      }),
      ...titles.map((title) => {
        const pick = () => {
          tips.input.value = shorten(title);
          tips.run(tips.input.value);
        };
        return [pick, el("ha-icon", { icon: "mdi:magnify" }), title];
      }),
    ]);
  }

  _offer(rows) {
    const tips = this._tips;
    tips.rows = rows.map(([pick, ...parts], index) => {
      const props = { className: "tip", id: `tips-${index}`, role: "option", onclick: () => void pick() };
      return { pick, node: el("div", props, ...parts) };
    });
    fill(tips.box, ...tips.rows.map((row) => row.node));
    tips.box.hidden = !rows.length;
    tips.input.ariaExpanded = String(rows.length > 0);
    this._mark(-1);
  }

  _mark(index) {
    const { input, rows } = this._tips;
    const row = rows[index]?.node;
    this._tips.active = index;
    for (const { node } of rows) node.ariaSelected = String(node === row);
    if (!row) input.removeAttribute("aria-activedescendant");
    else {
      input.setAttribute("aria-activedescendant", row.id);
      row.scrollIntoView({ block: "nearest" });
    }
  }

  _press(ev) {
    const { input, rows, active, run } = this._tips;
    const step = ev.key === "ArrowDown" ? 1 : ev.key === "ArrowUp" ? -1 : 0;
    if (ev.isComposing) return;
    if (step && rows.length) {
      ev.preventDefault();
      this._mark(((active + step + rows.length + 2) % (rows.length + 1)) - 1);
    } else if (ev.key === "Enter") {
      if (!rows[active]) run(input.value);
      else {
        ev.preventDefault();
        rows[active].pick();
      }
    } else if (ev.key === "Escape" || ev.key === "Tab") {
      if (ev.key === "Escape" && rows.length) ev.preventDefault();
      this._close();
    }
  }

  _close() {
    clearTimeout(this._wait);
    this._tipped = (this._tipped || 0) + 1;
    this._next = undefined;
    if (this._tips) this._offer([]);
  }

  _topic() {
    return this._theme === FEATURED ? undefined : this._theme;
  }

  async _refresh() {
    clearTimeout(this._again);
    clearTimeout(this._soon);
    this._again = this._soon = undefined;
    if (Date.now() - this._found?.at >= HALF_HOUR) this._search(this._found.query);
    this._busy = true;
    const asked = (this._asked = (this._asked || 0) + 1);
    let answer = null;
    try {
      const theme = this._topic() ? { theme: this._topic() } : {};
      answer = await this._hass.callWS({ type: "folders/overview", ...theme });
    } catch {
      answer = null;
    }
    if (asked !== this._asked) return;
    this._busy = false;
    this._data = answer?.status === "ok" ? { ...answer, at: Date.now() } : null;
    this._again = setTimeout(() => this._refresh(), this._data ? HALF_HOUR : 30000);
    this._draw();
  }

  _locate() {
    const { states, user } = this._hass;
    const own = (id) => id?.startsWith("person.") && states[id]?.attributes?.user_id === user?.id;
    if (!own(this._person)) this._person = user?.id ? Object.keys(states).find(own) : undefined;
    const { latitude: lat, longitude: lon } = states[this._person]?.attributes || {};
    return Number.isFinite(lat) && Number.isFinite(lon) ? { lat, lon } : null;
  }

  _track() {
    const { t } = this._texts();
    const place = this._locate();
    const was = this._area?.place;
    this._nearChip.title = place ? t.you : t.home;
    if (this._area && this.isConnected && (!place !== !was || (place && apart(place, was) > 0.2))) this._around();
  }

  _nearby() {
    this._area = this._area ? undefined : { stores: null };
    this._around();
    this._draw();
  }

  async _around() {
    clearTimeout(this._later);
    const area = this._area;
    const asked = (this._placed = (this._placed || 0) + 1);
    this._later = undefined;
    this._placing = Boolean(area);
    if (!area) return;
    const place = (area.place = this._locate());
    let answer = null;
    try {
      const at = place ? { latitude: place.lat, longitude: place.lon } : {};
      answer = await this._hass.callWS({ type: "folders/area", ...at, radius: this._config.radius });
    } catch {
      answer = null;
    }
    if (asked !== this._placed) return;
    const status = answer?.status;
    const stores = status === "ok" && answer.stores && typeof answer.stores === "object" ? answer.stores : {};
    this._placing = false;
    if (status === "ok" || status === "loading") {
      const near = new Map(Object.entries(stores).filter(([id]) => uuid(id)));
      Object.assign(area, { stores: near, at: place, loading: status === "loading" });
      this._later = setTimeout(() => this._around(), area.loading ? 15000 : HALF_HOUR);
    } else {
      this._area = undefined;
      this._note(this._texts().t.unavailable);
    }
    this._draw();
  }

  _draw() {
    const { language, t } = this._texts();
    const data = this._data || {};
    const stores = new Map(list(data.stores).map((store) => [store.id, store]));
    const named = new Map(list(data.stores).map((store) => [text(store.name), store]));
    this._names = new Map(list(data.categories).map((item) => [item.slug, text(item.name)]));
    const seen = new Set();
    const near = this._area?.stores;
    const pass = (store) => {
      const slugs = kinds(store?.categories);
      for (const slug of slugs) seen.add(slug);
      return slugs.some((slug) => !this._off.has(slug)) && (!near || near.has(store?.id));
    };
    const folders = list(data.folders).filter((folder) => uuid(folder.id));
    const theme = this._theme;
    const chosen = (folder) =>
      theme === undefined ||
      (theme === FEATURED ? folder.featured === true : Array.isArray(folder.themes) && folder.themes.includes(theme));
    const groups = new Map();
    for (const folder of folders.filter(chosen)) {
      groups.set(folder.store_id, [...(groups.get(folder.store_id) || []), folder]);
    }
    const rank = (folder) =>
      (folder.upcoming === true ? 1e15 + Date.parse(folder.valid_from) : -Date.parse(folder.valid_from)) || 0;
    const tiles = [...groups]
      .map(([id, folders]) => ({ id, store: stores.get(id), folders: folders.sort((a, b) => rank(a) - rank(b)) }))
      .filter((group) => pass(group.store))
      .sort((a, b) => text(a.store?.name).localeCompare(text(b.store?.name), language));
    const deals = list(data.deals)
      .filter((deal) => pass(named.get(text(deal.store))))
      .slice(0, 30);
    const watch = data.watch && typeof data.watch === "object" ? data.watch : {};
    const words = Array.isArray(watch.words) ? watch.words.filter((word) => typeof word === "string") : [];
    const found = list(watch.matches);
    const matches = found.filter((match) => pass(named.get(text(match.store))));
    const away = (match) => ({ ...match, distance: near.get(named.get(text(match.store))?.id), address: null });
    const mentions = list(watch.mentions).filter(
      (item) => uuid(item.folder_id) && pass(stores.get(item.store_id) || named.get(text(item.store))),
    );
    const themes = list(data.themes).filter((item) => SLUG.test(text(item.slug)));
    if (this._topic() && !themes.some((item) => item.slug === theme)) themes.push({ slug: theme });
    const star = theme === FEATURED || folders.some((folder) => folder.featured === true);
    this._row(
      this._themeRow,
      [
        ...(star ? [[FEATURED, t.featured, "mdi:star"]] : []),
        ...themes.map((item) => [item.slug, text(item.name) || item.slug, icon(THEME_ICONS, item.slug, "tag-outline")]),
      ],
      (slug) => slug === this._theme,
      (slug) => {
        const topic = this._topic();
        this._theme = slug === this._theme ? undefined : slug;
        this._draw();
        if (this._topic() !== topic) this._refresh();
      },
    );
    const filter = seen.size > 1 || [...seen].some((slug) => this._off.has(slug));
    this._row(this._kindRow, filter ? this._labels(seen) : [], (slug) => !this._off.has(slug), (slug) => {
      if (!this._off.delete(slug)) this._off.add(slug);
      this._draw();
    });
    this._nearChip.ariaPressed = String(Boolean(this._area));
    const items = (className, values) =>
      el("div", { className }, ...values.map((item) => this._item(item, item.folder_id, item.store, data.at)));
    const watched = words.length && 2 + matches.length + 2 * mentions.length;
    this._size = 2 + 7 * Math.ceil(tiles.length / 2) + (deals.length && 5) + watched;
    fill(
      this._rest,
      this._data === null && line("text", t.down),
      this._area?.loading && line("text", t.loading),
      words.length && line("heading", t.list),
      words.length && line("small pad", words.join(", ")),
      words.length && !found.length && line("text", t.quiet),
      words.length && matches.length && items("items", this._area?.at ? matches.map(away) : matches),
      words.length && mentions.length && line("heading", t.mentioned),
      words.length && mentions.length && this._hits(mentions, data.at),
      deals.length && line("heading", t.deals),
      deals.length && items("deals", deals),
      tiles.length && el("div", { className: "grid" }, ...tiles.map((group) => this._tile(group, data.at))),
      this._data && !folders.length && line("text", t.empty),
    );
  }

  _row(row, items, pressed, action) {
    const key = JSON.stringify(items);
    if (row.key !== key) {
      row.key = key;
      row.replaceChildren(
        ...items.map(([value, label, symbol, logo]) =>
          el(
            "button",
            { type: "button", className: "chip", value, onclick: () => void action(value) },
            symbol && el("ha-icon", { icon: symbol }),
            logo && el("img", { src: logo, alt: "" }),
            label,
          ),
        ),
      );
    }
    for (const chip of row.childNodes) chip.ariaPressed = String(pressed(chip.value));
    row.hidden = !items.length;
  }

  _labels(seen) {
    const { language, t } = this._texts();
    const label = (slug) =>
      slug === "other" ? t.other : this._names?.get(slug) || slug[0].toUpperCase() + slug.slice(1).replace(/-/g, " ");
    return [...seen]
      .map((slug) => [slug, label(slug), icon(KIND_ICONS, slug, "shape-outline")])
      .sort(([a, x], [b, y]) => (a === "other") - (b === "other") || x.localeCompare(y, language));
  }

  _tile({ id, store, folders: [first, ...rest] }, at) {
    const { language, t } = this._texts();
    const when = (folder) => period(this._hass, language, t, folder.valid_from, folder.valid_until);
    const cover = this._keep(first.cover, at);
    const show = el(
      "button",
      { type: "button", className: "tile", onclick: () => void this._read(first.id, 1, show) },
      el("img", cover ? { src: cover, alt: "", loading: "lazy" } : { alt: "" }),
      first.new === true && line("badge", t.new),
      line("name", text(store?.name)),
      line("", shortName(first.name, store?.name)),
      line("small", when(first)),
    );
    if (!rest.length) return el("div", { className: "cell" }, show);
    const others = el(
      "div",
      { className: "others", hidden: !this._wide.has(id) },
      ...rest.map((folder) => {
        const item = el(
          "button",
          { type: "button", className: "folder", onclick: () => void this._read(folder.id, 1, item) },
          line("", shortName(folder.name, store?.name)),
          line("small", when(folder)),
        );
        return item;
      }),
    );
    const more = button("more", `+${rest.length} ${t.more}`, () => {
      others.hidden = !others.hidden;
      more.ariaExpanded = String(!others.hidden);
      if (others.hidden) this._wide.delete(id);
      else this._wide.add(id);
    });
    more.ariaExpanded = String(!others.hidden);
    return el("div", { className: "cell" }, show, more, others);
  }

  _hits(rows, at, query) {
    const { language, t } = this._texts();
    return el(
      "div",
      { className: "hits" },
      ...rows.map((row) => {
        const pages = numbers(row.pages);
        const word = query || clean(row.word);
        const thumb = this._keep(row.thumb, at);
        const read = () => this._read(row.folder_id, pages[0] || 1, hit, word, pages.length ? pages : undefined);
        const hit = el(
          "button",
          { type: "button", className: "row", onclick: read },
          el("img", thumb ? { src: thumb, alt: "", loading: "lazy" } : { alt: "" }),
          el(
            "div",
            {},
            line("name", text(row.store)),
            line("", shortName(row.folder, row.store)),
            line("small", [!query && word, where(t, pages)].filter(Boolean).join(": ")),
            line("small", period(this._hass, language, t, row.valid_from, row.valid_until)),
          ),
        );
        return hit;
      }),
    );
  }

  _item(item, folder, store, at, actions) {
    const { language, t } = this._texts();
    const image = this._keep(item.image, at);
    const title = text(item.title);
    const cost = money(language, item.sale_price) || money(language, item.price);
    const details = [text(item.store), period(this._hass, language, t, item.valid_from, item.valid_until)];
    const parts = [
      el("img", image ? { src: image, alt: "", loading: "lazy" } : { alt: "" }),
      line("name", title),
      line("", price(t, language, item)),
      line("small", text(item.description)),
      line("small", details.filter(Boolean).join(", ")),
      line("small", !actions && far(language, item)),
    ];
    const target = uuid(folder);
    const opens = target && !actions;
    const read = (opener) => this._read(target, item.page, opener);
    const props = opens ? { type: "button", className: "show", onclick: () => void read(show) } : { className: "show" };
    const show = el(opens ? "button" : "div", props, ...parts);
    const go = target && actions && button("open", t.open, () => read(go));
    const label = [text(store), cost].filter(Boolean).join(", ");
    const entry = label ? `${title} (${label})` : title;
    const add = this._list && title && button("add", t.add, () => this._add(this._list, entry, `${t.added}: ${title}`));
    return el("div", { className: "item" }, show, go, add);
  }

  async _add(entity, item, done) {
    try {
      await this._hass.callService("todo", "add_item", { item }, { entity_id: entity }, false);
      this._note(done);
    } catch (err) {
      this._note(await this._explain(err));
    }
  }

  _follow(value) {
    const { t } = this._texts();
    const word = clean(value).toLowerCase();
    if (!fits(bare(word))) this._note(t.short);
    else this._add(this._watchList, word, `${t.watched}: ${word}`);
  }

  _note(message) {
    this.dispatchEvent(new CustomEvent("hass-notification", { detail: { message }, bubbles: true, composed: true }));
  }

  async _explain(err) {
    const { translation_domain: domain, translation_key: key, translation_placeholders: values } = err || {};
    let message = "";
    try {
      const localize = domain && key && (await this._hass.loadBackendTranslation("exceptions", domain));
      message = (localize && localize(`component.${domain}.exceptions.${key}.message`, values || {})) || "";
    } catch {
      message = "";
    }
    return message || text(err?.message) || this._texts().t.lost;
  }

  async _search(value) {
    const { t } = this._texts();
    const query = bare(value);
    const asked = (this._sought = (this._sought || 0) + 1);
    this._close();
    if (query !== this._found?.query) this._pick = undefined;
    this._found = { query, note: fits(query) ? t.busy : t.short };
    this._drawFound();
    if (!fits(query)) return;
    let answer = null;
    try {
      answer = await this._hass.callWS({ type: "folders/search", query, scope: this._scope ? "followed" : "all" });
    } catch {
      answer = null;
    }
    if (asked !== this._sought) return;
    const ok = answer?.status === "ok";
    const { results, folders, stores } = ok ? answer : {};
    const more = ok && answer.more === true;
    this._found = { query, note: ok ? "" : t.cannot, results, folders, stores, more, at: Date.now() };
    this._drawFound();
  }

  _drawFound() {
    const found = this._found;
    const { t } = this._texts();
    const results = list(found?.results);
    const chains = list(found?.stores).filter((store) => uuid(store.folder_id));
    const hits = list(found?.folders).filter((hit) => uuid(hit.folder_id));
    const close = () => {
      this._sought = (this._sought || 0) + 1;
      this._found = undefined;
      this._drawFound();
      this._input.focus();
    };
    const sort = el("input", {
      type: "checkbox",
      checked: this._closest === true,
      onchange: () => {
        this._closest = sort.checked;
        this._drawItems();
      },
    });
    const near = results.some((item) => Number.isFinite(item.distance));
    const chain = (store) => {
      const logo = this._keep(store.logo, found.at);
      const props = { type: "button", className: "chip", onclick: () => void this._read(store.folder_id, 1, chip) };
      const chip = el("button", props, logo && el("img", { src: logo, alt: "" }), text(store.name));
      return chip;
    };
    this._results.hidden = !found;
    fill(
      this._results,
      found &&
        el(
          "div",
          { className: "head pad" },
          line("name", found.query),
          near && el("label", { className: "toggle" }, sort, t.nearest),
          button("step", t.close, close),
        ),
      found?.note && line("text", found.note),
      chains.length && el("div", { className: "chips" }, ...chains.map(chain)),
      this._pickRow,
      this._shown,
      found && !found.note && !results.length && line("text", t.nothing),
      found?.more && line("text", t.many),
      hits.length && line("heading", t.found),
      hits.length && this._hits(hits, found.at, found.query),
    );
    this._drawItems();
  }

  _drawItems() {
    const found = this._found;
    const { language, t } = this._texts();
    const results = list(found?.results);
    const kind = (item) => text(item.product_category);
    const counts = new Map();
    for (const item of results) counts.set(kind(item), (counts.get(kind(item)) || 0) + 1);
    const pick = counts.has(this._pick) ? this._pick : undefined;
    const label = (value) => value || t.other;
    const chips = [...counts]
      .sort(([a, x], [b, y]) => y - x || label(a).localeCompare(label(b), language))
      .map(([value]) => [value, label(value)]);
    this._row(this._pickRow, counts.size > 1 ? chips : [], (value) => value === pick, (value) => {
      this._pick = value === this._pick ? undefined : value;
      this._drawItems();
    });
    const shown = results.filter((item) => pick === undefined || kind(item) === pick);
    const distance = (item) => (Number.isFinite(item.distance) ? item.distance : Infinity);
    if (this._closest) shown.sort((a, b) => distance(a) - distance(b) || 0);
    fill(this._shown, ...shown.map((item) => this._item(item, item.folder_id, item.store, found.at)));
    this._shown.hidden = !shown.length;
  }

  _read(id, page, opener, query, pages) {
    const host = this._config?.view === "map" ? this._body : this._card;
    if (!host || !uuid(id)) return;
    const { t } = this._texts();
    this._viewer?.root.remove();
    const back = button("step", t.back, () => this._back());
    const info = el("div");
    const body = el("div", { className: "frame" }, line("text", t.wait));
    const root = el(
      "div",
      { className: host === this._body ? "viewer over" : "viewer", tabIndex: -1, onkeydown: (ev) => this._key(ev) },
      el("div", { className: "head" }, back, info),
      body,
    );
    const start = Number.isInteger(page) && page > 0 ? page : 1;
    this._viewer = { id, page: start, opener, root, info, body, zoom: false, query: "", hits: [] };
    if (this._main) this._main.hidden = true;
    host.append(root);
    back.focus();
    this._load(this._viewer);
    if (fits(clean(query))) this._find(this._viewer, query, pages);
  }

  async _load(viewer) {
    let answer = null;
    try {
      answer = await this._hass.callWS({ type: "folders/pages", folder_id: viewer.id });
    } catch {
      answer = null;
    }
    if (viewer !== this._viewer) return;
    const { language, t } = this._texts();
    const at = Date.now();
    const folder = answer?.folder && typeof answer.folder === "object" ? answer.folder : null;
    const ok = answer?.status === "ok" && folder && Array.isArray(answer.pages);
    const pages = ok ? answer.pages.map((path) => this._keep(path, at) || "") : [];
    if (folder) {
      const home = text(folder.website);
      const site = text(folder.url).startsWith(SITE) && link(t.site, folder.url);
      const web = home.length <= 200 && WEB.test(home) && link(t.website, home);
      fill(
        viewer.info,
        line("name", text(folder.store)),
        line("", shortName(folder.name, folder.store)),
        line("small", period(this._hass, language, t, folder.valid_from, folder.valid_until)),
        (site || web) && el("div", { className: "links" }, site, web),
      );
    }
    if (!pages.length) {
      viewer.image = undefined;
      fill(viewer.body, line("text", answer?.status === "unknown" ? t.gone : t.broken));
      return;
    }
    const thumbs = Array.isArray(answer.thumbs) ? answer.thumbs : [];
    Object.assign(viewer, {
      folder,
      pages,
      thumbs: pages.map((_, index) => this._keep(thumbs[index], at) || ""),
      offers: list(answer.offers),
      at,
    });
    if (!viewer.image) this._frame(viewer);
    this._go(viewer.page, viewer.grid);
  }

  _frame(viewer) {
    const { t } = this._texts();
    const step = (label, delta) => button("step", label, () => this._go(viewer.page + delta));
    const swipe = (ev) => {
      const [x, y] = viewer.start || [];
      const dx = ev.clientX - x;
      viewer.start = null;
      if (Math.abs(dx) >= 50 && Math.abs(dx) > Math.abs(ev.clientY - y)) this._go(viewer.page + (dx < 0 ? 1 : -1));
    };
    const finder = el("input", {
      type: "search",
      value: viewer.query,
      placeholder: t.look,
      ariaLabel: t.look,
      maxLength: 40,
      enterKeyHint: "search",
      onkeydown: (ev) => {
        ev.stopPropagation();
        if (ev.key === "Enter" && !ev.isComposing) this._find(viewer, finder.value);
      },
    });
    Object.assign(viewer, {
      prev: step(t.previous, -1),
      next: step(t.next, 1),
      count: el("span"),
      zoomer: button("step", "", () => {
        viewer.zoom = !viewer.zoom;
        this._go(viewer.page);
      }),
      all: button("step", t.thumbs, () => this._go(viewer.page, !viewer.grid)),
      found: el("div", { className: "found" }),
      image: el("img", { alt: "", draggable: false }),
      preload: el("img", { alt: "", hidden: true }),
      sheet: el("div", { className: "sheet" }),
      here: el("div"),
    });
    viewer.area = el(
      "div",
      {
        onpointerdown: (ev) => {
          viewer.start = [ev.clientX, ev.clientY];
        },
        onpointerup: swipe,
        onpointercancel: () => {
          viewer.start = null;
        },
      },
      viewer.image,
    );
    fill(
      viewer.body,
      el("div", { className: "controls" }, viewer.prev, viewer.count, viewer.next, viewer.zoomer, viewer.all),
      el("div", { className: "search" }, finder, button("go", t.find, () => this._find(viewer, finder.value))),
      viewer.found,
      viewer.area,
      viewer.sheet,
      viewer.preload,
      viewer.here,
    );
    this._drawFind(viewer);
  }

  async _find(viewer, value, pages) {
    const { t } = this._texts();
    const query = clean(value);
    const asked = (viewer.asked = (viewer.asked || 0) + 1);
    Object.assign(viewer, { query, note: fits(query) ? t.busy : t.short, hits: [] });
    this._drawFind(viewer);
    if (!fits(query)) return;
    let answer = pages ? { status: "ok", pages } : null;
    try {
      answer = answer || (await this._hass.callWS({ type: "folders/find", folder_id: viewer.id, query }));
    } catch {
      answer = null;
    }
    if (viewer !== this._viewer || asked !== viewer.asked) return;
    const ok = answer?.status === "ok";
    const hits = numbers(ok && answer.pages);
    Object.assign(viewer, { note: !ok ? t.blind : hits.length ? "" : t.missed, hits });
    this._drawFind(viewer);
  }

  _drawFind(viewer) {
    if (!viewer.found) return;
    const { t } = this._texts();
    const hits = viewer.hits.filter((page) => page <= viewer.pages.length);
    const chip = (page) => button("chip", `${t.p} ${page}`, () => this._go(page));
    fill(viewer.found, line("small", viewer.note), ...hits.map(chip));
    viewer.found.hidden = !viewer.note && !hits.length;
  }

  _go(page, grid = false) {
    const viewer = this._viewer;
    viewer.page = Math.max(1, Math.min(viewer.pages.length, page));
    viewer.grid = grid;
    if (Date.now() - viewer.at >= HALF_HOUR) {
      this._load(viewer);
      return;
    }
    const { t } = this._texts();
    const { pages, page: now } = viewer;
    viewer.image.src = pages[now - 1];
    viewer.image.alt = `${t.page} ${now}`;
    if (pages[now] && !grid) viewer.preload.src = pages[now];
    viewer.count.textContent = `${t.page} ${now} ${t.of} ${pages.length}`;
    viewer.prev.disabled = now === 1;
    viewer.next.disabled = now === pages.length;
    viewer.zoomer.textContent = viewer.zoom ? t.zoomOut : t.zoomIn;
    viewer.all.ariaPressed = String(grid);
    viewer.area.className = viewer.zoom ? "page zoomed" : "page";
    viewer.area.hidden = grid;
    viewer.sheet.hidden = !grid;
    const thumb = (src, index) =>
      el(
        "button",
        {
          type: "button",
          className: "thumb",
          ...(index + 1 === now && { ariaCurrent: "page" }),
          onclick: () => {
            this._go(index + 1);
            viewer.root.focus();
          },
        },
        el("img", src ? { src, alt: "", loading: "lazy" } : { alt: "" }),
        line("small", String(index + 1)),
      );
    fill(viewer.sheet, ...(grid ? viewer.thumbs.map(thumb) : []));
    const offers = grid ? [] : viewer.offers.filter((offer) => offer.page === now);
    const items = offers.map((offer) => this._item(offer, null, viewer.folder.store, viewer.at));
    fill(
      viewer.here,
      items.length && line("heading", t.here),
      items.length && el("div", { className: "items" }, ...items),
    );
    if (this.shadowRoot.activeElement?.disabled) viewer.root.focus();
  }

  _key(ev) {
    const step = ev.key === "ArrowLeft" ? -1 : ev.key === "ArrowRight" ? 1 : 0;
    if (step && this._viewer?.image) {
      ev.preventDefault();
      this._go(this._viewer.page + step);
    } else if (ev.key === "Escape") this._back();
  }

  _back() {
    const viewer = this._viewer;
    this._viewer = undefined;
    viewer?.root.remove();
    if (this._main) this._main.hidden = false;
    viewer?.opener?.focus();
  }

  _link() {
    const url = new URL(window.location.href);
    const params = url.searchParams;
    const keys = ["folders_folder", "folders_page", "folders_query"];
    if (!keys.some((key) => params.has(key))) return;
    const [id, page, query] = keys.map((key) => params.get(key));
    this._pending = { id, page: Number(page || 1), query };
    for (const key of keys) params.delete(key);
    window.history.replaceState(window.history.state, "", `${url.pathname}${url.search}${url.hash}`);
  }

  _pend() {
    const pending = this._pending;
    if (pending && this._hass && (this._config?.view === "map" ? this._body : this._card)) {
      this._pending = undefined;
      this._read(pending.id, pending.page, undefined, pending.query);
    }
  }

  _start() {
    const view = this.isConnected && this._config?.view;
    if (view === "folders" && this._hass && !this._busy && !this._again) this._refresh();
    if (view === "folders" && this._hass && this._area && !this._placing && !this._later) this._around();
    if (view !== "map" || this._timer) return;
    this._timer = setInterval(() => this._tick(), 1000);
    if (!this._map && !this._token) this._build();
    else if (this._hunt) this._seek(this._hunt.query);
  }

  _stop() {
    clearInterval(this._timer);
    clearTimeout(this._again);
    clearTimeout(this._soon);
    clearTimeout(this._near);
    clearTimeout(this._later);
    this._timer = this._again = this._soon = this._near = this._later = this._seen = this._token = undefined;
    this._busy = this._placing = false;
    this._asked = (this._asked || 0) + 1;
    this._placed = (this._placed || 0) + 1;
    this._hunted = (this._hunted || 0) + 1;
    this._ready?.(false);
    this._close();
  }

  async _build() {
    const token = (this._token = {});
    let ready = false;
    let wait;
    try {
      const helpers = await window.loadCardHelpers();
      if (token !== this._token) return;
      helpers.createCardElement({ type: "map", geo_location_sources: ["folders"] });
      ready = await new Promise((resolve) => {
        this._ready = resolve;
        wait = setTimeout(() => resolve(false), 10000);
        customElements.whenDefined("ha-map").then(() => resolve(true));
      });
    } catch {
      ready = false;
    }
    clearTimeout(wait);
    if (token !== this._token) return;
    this._token = undefined;
    const { t } = this._texts();
    const style = el("style", { textContent: STYLE });
    if (!ready) {
      clearInterval(this._timer);
      this._timer = undefined;
      const message = el("div", { className: "text", textContent: t.failed });
      this.shadowRoot.replaceChildren(style, el("ha-card", {}, message));
      return;
    }
    const map = Object.assign(document.createElement("ha-map"), {
      zoom: this._config.zoom,
      autoFit: false,
      themeMode: "auto",
    });
    this._hint = el("div", { className: "hint", hidden: true });
    this._panel = el("div", { className: "panel", hidden: true });
    this._footer = el("div", { className: "footer" });
    this._kindRow = el("div", { className: "set" });
    this._storeRow = el("div", { className: "set" });
    this._mineText = el("span");
    const finder = el("input", { type: "search", maxLength: 40, enterKeyHint: "search" });
    this._finder = finder;
    this._seeker = button("go", "", () => this._seek(finder.value));
    const mine = el("input", {
      type: "checkbox",
      checked: this._mine === true,
      onchange: () => {
        this._mine = mine.checked;
        this._show(...this._raw);
        if (this._hunt) this._seek(this._hunt.query);
      },
    });
    const area = el("div", { className: "map" }, map, this._hint);
    area.addEventListener("context-request", (ev) => this._provide(ev));
    area.addEventListener("hass-more-info", (ev) => {
      const id = ev.detail?.entityId;
      if (typeof id === "string" && Object.hasOwn(this._shops, id)) {
        ev.stopPropagation();
        this._open(this._shops[id].shop, this._shops[id].store, this._raw[2]);
      }
    });
    area.addEventListener("map-clicked", () => this._shut());
    this._map = map;
    this._pointer = el("style", { textContent: POINTER });
    const field = this._field(finder, (value) => this._seek(value));
    const search = el("div", { className: "search line" }, field, this._seeker);
    const toggle = el("label", { className: "toggle" }, mine, this._mineText);
    const stores = el("div", { className: "bar" }, el("div", { className: "chips" }, this._storeRow));
    const bar = el("div", { className: "bar" }, el("div", { className: "chips" }, this._kindRow), toggle);
    this._body = el("div", { className: "body" }, search, area, stores, bar, this._panel);
    this.shadowRoot.replaceChildren(style, el("ha-card", { className: "maps" }, this._body, this._footer));
    this._sync();
    this._bar();
    this._pend();
  }

  _provide(ev) {
    if (ev.context !== "states") return;
    ev.stopPropagation();
    const callback = ev.callback;
    const unsubscribe = () => this._consumers.delete(callback);
    if (ev.subscribe) this._consumers.set(callback, unsubscribe);
    callback(this._states || this._hass?.states || {}, ev.subscribe ? unsubscribe : undefined);
  }

  _sync() {
    const hass = this._hass;
    if (!this._map || !hass) return;
    const states = { ...hass.states };
    for (const [id, { shop, store, logo }] of Object.entries(this._shops)) {
      states[id] = {
        entity_id: id,
        state: "",
        attributes: {
          latitude: shop.lat,
          longitude: shop.lon,
          friendly_name: text(store.name),
          entity_picture: logo,
          source: "folders",
        },
      };
    }
    this._states = states;
    this._map.entities = [...Object.keys(this._shops), "zone.home"];
    this._map.hass = { ...hass, states };
    for (const [callback, unsubscribe] of this._consumers) callback(states, unsubscribe);
    const root = this._map.shadowRoot;
    if (root && this._pointer.parentNode !== root) root.append(this._pointer);
  }

  _bar() {
    const { t } = this._texts();
    this._footer.textContent = t.footer;
    this._mineText.textContent = t.mine;
    this._seeker.textContent = t.find;
    Object.assign(this._finder, { placeholder: t.search, ariaLabel: t.search });
    this._tips.box.ariaLabel = t.tips;
    this._row(this._kindRow, this._labels(this._slugs || []), (slug) => !this._off.has(slug), (slug) => {
      if (!this._off.delete(slug)) this._off.add(slug);
      this._show(...this._raw);
    });
    this._row(this._storeRow, this._chains || [], (id) => !this._gone.has(id), (id) => {
      if (!this._gone.delete(id)) this._gone.add(id);
      this._show(...this._raw);
    });
  }

  async _name() {
    this._names = new Map();
    try {
      const answer = await this._hass.callWS({ type: "folders/overview" });
      this._names = new Map(list(answer?.categories).map((item) => [item.slug, text(item.name)]));
    } catch {
      return;
    }
    if (this._map) this._bar();
  }

  _where() {
    const map = this._map;
    let lat;
    let lon;
    let zoom;
    if (typeof map.getView === "function") {
      const view = map.getView();
      [lat, lon] = Array.isArray(view?.center) ? view.center : [];
      zoom = view?.zoom;
    } else if (map.leafletMap) {
      const center = map.leafletMap.getCenter();
      [lat, lon, zoom] = [center?.lat, center?.lng, map.leafletMap.getZoom()];
    }
    return [lat, lon, zoom].every(Number.isFinite) ? { lat, lon, zoom } : null;
  }

  _tick() {
    if (!this._map || document.hidden) return;
    const view = this._where();
    if (!view) return;
    const key = [view.lat, view.lon, view.zoom, this._map.clientWidth, this._map.clientHeight].join();
    if (key !== this._seen) {
      this._seen = key;
      this._settled = false;
    } else if (!this._settled) {
      this._settled = true;
      this._ask(view);
    }
  }

  _box({ lat, lon, zoom }) {
    const width = this._map.clientWidth;
    const height = this._map.clientHeight;
    if (!(width > 0 && height > 0)) return null;
    const size = 256 * 2 ** zoom;
    const sin = Math.sin((Math.max(-85, Math.min(85, lat)) * Math.PI) / 180);
    const x = ((lon + 180) / 360) * size;
    const y = (0.5 - Math.log((1 + sin) / (1 - sin)) / (4 * Math.PI)) * size;
    const toLat = (py) => (Math.atan(Math.sinh(Math.PI * (1 - (2 * py) / size))) * 180) / Math.PI;
    const toLon = (px) => Math.max(-180, Math.min(180, (px / size) * 360 - 180));
    return {
      south: toLat(y + height / 2),
      west: toLon(x - width / 2),
      north: toLat(y - height / 2),
      east: toLon(x + width / 2),
    };
  }

  async _ask(view) {
    clearTimeout(this._again);
    this._again = undefined;
    this._last = view;
    if (Date.now() - this._hunt?.at >= HALF_HOUR) {
      this._seek(this._hunt.query);
      return;
    }
    const asked = (this._asked = (this._asked || 0) + 1);
    const { t } = this._texts();
    if (view.zoom < 11) {
      this._show([], {});
      this._say(t.zoom);
    }
    const box = view.zoom >= 11 && this._box(view);
    if (!box) {
      this._again = setTimeout(() => this._ask(this._last), HALF_HOUR);
      return;
    }
    const ids = this._hunt?.ids || [];
    let answer = null;
    try {
      answer = await this._hass.callWS({ type: "folders/shops", ...box, ...(ids.length && { stores: ids }) });
    } catch {
      answer = null;
    }
    if (asked !== this._asked) return;
    const status = answer?.status;
    const ok = status === "ok";
    this._show(ok ? answer.shops : [], ok ? answer.stores : {}, Date.now());
    if (ok) this._say(answer.more ? t.all : "");
    else this._say(status === "zoom" ? t.zoom : status === "loading" ? t.loading : t.unavailable);
    if (ok && !this._names) this._name();
    const soon = !answer || status === "loading" || status === "not_loaded";
    this._again = setTimeout(() => this._ask(this._last), soon ? 15000 : HALF_HOUR);
  }

  _say(message) {
    this._hint.textContent = message;
    this._hint.hidden = !message;
  }

  _keep(value, at) {
    if (!SIGNED.test(text(value))) return undefined;
    const base = value.split("?")[0];
    const now = Date.now();
    const kept = this._paths.get(base);
    if (kept && (kept.at >= at || now - kept.at < HALF_HOUR)) return kept.path;
    for (const [key, item] of this._paths.size > 500 ? this._paths : []) {
      if (now - item.at >= HALF_HOUR) this._paths.delete(key);
    }
    this._paths.set(base, { path: value, at });
    return value;
  }

  _show(shops, stores, at) {
    this._raw = [shops, stores, at];
    const entries = {};
    const seen = new Set();
    const chains = new Map();
    for (const shop of Array.isArray(shops) ? shops : []) {
      const store = stores && typeof stores === "object" && Object.hasOwn(stores, shop?.store) && stores[shop.store];
      const valid = /^[nwr]\d{1,15}$/.test(shop?.id) && Number.isFinite(shop.lat) && Number.isFinite(shop.lon);
      if (!valid || !store || typeof store !== "object") continue;
      const slugs = kinds(store.categories);
      for (const slug of slugs) seen.add(slug);
      if (slugs.every((slug) => this._off.has(slug)) || (this._mine && store.followed !== true)) continue;
      const logo = this._keep(store.logo, at);
      chains.set(shop.store, [shop.store, text(store.name), undefined, logo]);
      if (!this._gone.has(shop.store)) entries[`geo_location.folders_${shop.id}`] = { shop, store, logo };
    }
    const { language } = this._texts();
    this._slugs = seen;
    this._chains = [...chains.values()].sort((a, b) => a[1].localeCompare(b[1], language));
    this._bar();
    const key = JSON.stringify(
      Object.entries(entries).map(([id, { shop, store, logo }]) => [id, shop.lat, shop.lon, text(store.name), logo]),
    );
    this._shops = entries;
    if (key !== this._drawn) {
      this._drawn = key;
      this._sync();
    }
  }

  _open(shop, store, at) {
    const { language, t } = this._texts();
    const hunt = this._hunt;
    const found = hunt ? list(hunt.results).filter((item) => item.store_id === shop.store) : [];
    const folder = store.folder && typeof store.folder === "object" ? store.folder : null;
    const cover = folder && this._keep(folder.cover, at);
    const target = uuid(folder?.id);
    const read = target && button("", t.open, () => this._read(target, 1, read));
    const hours = text(shop.hours);
    const items = found.map((item) => this._item(item, item.folder_id, item.store, hunt.at, true));
    this._spot = shop;
    fill(
      this._panel,
      items.length && el("div", { className: "items" }, ...items),
      el(
        "div",
        { className: "shop" },
        cover ? el("img", { src: cover, alt: "" }) : el("div"),
        el(
          "div",
          {},
          line("name", text(store.name)),
          line("small", text(shop.address)),
          line("small", hours && `${t.hours}: ${hours}`),
          folder && line("", shortName(folder.name, store.name)),
          folder && line("small", period(this._hass, language, t, folder.valid_from, folder.valid_until)),
          el("div", { className: "actions" }, read, button("", t.close, () => this._shut())),
        ),
      ),
    );
    this._panel.hidden = false;
    (this._map.panTo ? this._map : this._map.leafletMap)?.panTo([shop.lat, shop.lon]);
  }

  _shut() {
    this._spot = undefined;
    if (this._hunt) this._drawHunt();
    else this._panel.hidden = true;
  }

  async _seek(value) {
    const { t } = this._texts();
    const query = bare(value);
    const asked = (this._hunted = (this._hunted || 0) + 1);
    clearTimeout(this._near);
    this._close();
    this._spot = undefined;
    this._hunt = { query, note: fits(query) ? t.busy : t.short, results: [], ids: [] };
    this._drawHunt();
    let answer = null;
    if (fits(query)) {
      try {
        answer = await this._hass.callWS({ type: "folders/search", query, scope: this._mine ? "followed" : "all" });
      } catch {
        answer = null;
      }
      if (asked !== this._hunted) return;
      const ok = answer?.status === "ok";
      const results = ok ? list(answer.results) : [];
      const ids = [...new Set(results.map((item) => uuid(item.store_id)).filter(Boolean))].slice(0, 60);
      this._hunt = { query, note: !ok ? t.cannot : ids.length ? t.busy : t.nothing, results, ids, at: Date.now() };
      this._drawHunt();
      if (ids.length) this._nearest(asked);
    }
    if (this._last) this._ask(this._last);
  }

  async _nearest(asked) {
    clearTimeout(this._near);
    const hunt = this._hunt;
    const center = this._where();
    let answer = null;
    try {
      const place = center ? { latitude: center.lat, longitude: center.lon } : {};
      answer = await this._hass.callWS({ type: "folders/nearest", stores: hunt.ids, ...place, limit: 10 });
    } catch {
      answer = null;
    }
    if (asked !== this._hunted) return;
    const { t } = this._texts();
    const status = answer?.status;
    const shops = status === "ok" ? list(answer.shops) : [];
    const note = status === "ok" ? !shops.length && t.far : status === "loading" ? t.loading : t.unavailable;
    Object.assign(hunt, { shops, stores: status === "ok" && answer.stores, note, near: Date.now() });
    if (status === "loading") this._near = setTimeout(() => this._nearest(asked), 15000);
    this._drawHunt();
  }

  _drawHunt() {
    const hunt = this._hunt;
    if (!hunt || this._spot || !this._panel) return;
    const { language, t } = this._texts();
    const stores = hunt.stores && typeof hunt.stores === "object" ? hunt.stores : {};
    const rows = list(hunt.shops).map((shop) => {
      const store = Object.hasOwn(stores, shop.store) && stores[shop.store];
      if (!store || typeof store !== "object" || !Number.isFinite(shop.lat) || !Number.isFinite(shop.lon)) return null;
      const [first, ...more] = hunt.results.filter((item) => item.store_id === shop.store);
      const logo = this._keep(store.logo, hunt.near);
      const hours = text(shop.hours);
      return el(
        "button",
        { type: "button", className: "row near", onclick: () => void this._open(shop, store, hunt.near) },
        el("img", logo ? { src: logo, alt: "" } : { alt: "" }),
        el(
          "div",
          {},
          line("name", text(store.name)),
          line("small", far(language, shop)),
          line("small", hours && `${t.hours}: ${hours}`),
          first && line("", text(first.title)),
          first && line("", price(t, language, first)),
          first && line("small", text(first.description)),
          more.length && line("small", `+${more.length} ${t.more}`),
        ),
      );
    });
    const close = button("step", t.close, () => this._quit());
    fill(
      this._panel,
      el("div", { className: "head" }, line("name", `${t.near} ${hunt.query}`), close),
      line("small", hunt.note),
      ...rows,
    );
    this._panel.hidden = false;
  }

  _quit() {
    this._hunted = (this._hunted || 0) + 1;
    clearTimeout(this._near);
    this._hunt = this._spot = this._near = undefined;
    this._panel.hidden = true;
    this._finder.focus();
    if (this._last) this._ask(this._last);
  }
}

const register = () => {
  if (customElements.get("folders-card")) return;
  customElements.define("folders-card", FoldersCard);
  (window.customCards = window.customCards || []).push({
    type: "folders-card",
    name: "Folders",
    description: "Folders, best deals and product search of your stores, or a map of the shops with their folders.",
  });
};

if (customElements.get("home-assistant")) register();
else customElements.whenDefined("home-assistant").then(register);
