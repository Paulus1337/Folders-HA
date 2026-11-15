const STYLE = `
:host { display: block; height: 100%; }
ha-card { display: flex; flex-direction: column; height: 100%; box-sizing: border-box; overflow: hidden; }
[hidden] { display: none !important; }
button { padding: 0; border: 0; background: none; color: inherit; font: inherit; text-align: left; cursor: pointer; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 12px; padding: 16px; }
.tile { display: grid; gap: 2px; align-content: start; }
.tile img, .panel img {
  width: 100%; aspect-ratio: 3 / 4; object-fit: cover; border-radius: 8px;
  background: var(--secondary-background-color);
}
.name { font-weight: 500; }
.small { color: var(--secondary-text-color); font-size: 0.9em; }
.offers { display: grid; gap: 6px; padding: 0 16px 16px; }
.text { padding: 16px; }
.map { position: relative; flex: 1; min-height: 300px; }
ha-map { position: absolute; inset: 0; height: auto; z-index: 0; }
.hint {
  position: absolute; top: 8px; left: 50%; transform: translateX(-50%); z-index: 1000; padding: 4px 12px;
  border-radius: 16px; background: var(--card-background-color); pointer-events: none;
}
.panel {
  display: grid; grid-template-columns: 96px 1fr; gap: 12px; padding: 12px 16px;
  border-top: 1px solid var(--divider-color);
}
.actions { display: flex; gap: 16px; margin-top: 8px; }
.actions button { color: var(--primary-color); }
.footer { padding: 4px 16px 8px; color: var(--secondary-text-color); font-size: 0.8em; }
`;
const TEXTS = {
  en: {
    until: "until",
    from: "from",
    more: "more",
    was: "was",
    none: "You follow no stores yet. Choose them in Settings > Devices & services > Folders > Configure.",
    empty: "No folders right now.",
    zoom: "Zoom in to see the shops",
    loading: "Loading the shops of the Netherlands, this takes a few minutes",
    unavailable: "Shops are not available right now",
    all: "Zoom in to see all shops",
    failed: "The map could not be loaded.",
    open: "Open folder",
    store: "Open store page",
    close: "Close",
    footer: "Shops (c) OpenStreetMap contributors, folders from folders.nl",
  },
  nl: {
    until: "t/m",
    from: "vanaf",
    more: "meer",
    was: "was",
    none: "Je volgt nog geen winkels. Kies ze via Instellingen > Apparaten & diensten > Folders > Configureren.",
    empty: "Er zijn nu geen folders.",
    zoom: "Zoom in om de winkels te zien",
    loading: "De winkels van Nederland worden geladen, dit duurt een paar minuten",
    unavailable: "De winkels zijn nu niet beschikbaar",
    all: "Zoom in om alle winkels te zien",
    failed: "De kaart kon niet worden geladen.",
    open: "Folder openen",
    store: "Winkelpagina openen",
    close: "Sluiten",
    footer: "Winkels (c) OpenStreetMap-bijdragers, folders van folders.nl",
  },
};
const SITE = "https://folders.nl/";
const IMAGES = "/api/folders/image/";
const HALF_HOUR = 1800000;

const el = (tag, props, ...children) => {
  const node = Object.assign(document.createElement(tag), props);
  node.append(...children.filter(Boolean));
  return node;
};
const text = (value) => (typeof value === "string" ? value : "");
const line = (className, value) => value && el("div", { className, textContent: value });
const open = (url) => {
  if (typeof url === "string" && url.startsWith(SITE)) window.open(url, "_blank", "noopener,noreferrer");
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
  typeof value === "number" && Number.isFinite(value)
    ? new Intl.NumberFormat(language, { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(value)
    : "";
const offerLine = (t, language, offer) => {
  const sale = money(language, offer.sale_price);
  const price = money(language, offer.price);
  const was = sale && price && sale !== price ? ` (${t.was} ${price})` : "";
  const shown = sale || price;
  return `${text(offer.store)}: ${text(offer.title)}${shown ? `, ${shown}${was}` : ""}`;
};

class FoldersCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._paths = new Map();
    this._consumers = new Map();
    this._shops = {};
  }

  setConfig(config) {
    const view = config?.view ?? "folders";
    const zoom = config?.zoom ?? 14;
    if (view !== "folders" && view !== "map") throw new Error("view must be folders or map");
    if (typeof zoom !== "number" || !(zoom >= 1 && zoom <= 20)) throw new Error("zoom must be a number from 1 to 20");
    this._stop();
    this._config = { view, zoom };
    this._map = this._used = this._drawn = undefined;
    this._shops = {};
    this.shadowRoot.replaceChildren();
    this._start();
    if (this._hass) this.hass = this._hass;
  }

  getCardSize() {
    return this._config?.view === "map" ? 8 : (this._size ?? 6);
  }

  getGridOptions() {
    return this._config?.view === "map" ? { columns: "full", rows: 8, min_rows: 8 } : { columns: "full" };
  }

  static getStubConfig() {
    return {};
  }

  connectedCallback() {
    this._start();
  }

  disconnectedCallback() {
    this._stop();
  }

  set hass(hass) {
    const old = this._hass;
    this._hass = hass;
    if (this._config?.view === "folders") this._render();
    else if (this._map && (!old || ["themes", "language", "locale"].some((key) => old[key] !== hass[key]))) {
      this._sync();
    }
  }

  _texts() {
    const language = this._hass?.locale?.language || this._hass?.language || "en";
    return { language, t: TEXTS[/^nl/i.test(language) ? "nl" : "en"] };
  }

  _render() {
    const hass = this._hass;
    const { language, t } = this._texts();
    const mine = Object.values(hass.entities || {}).filter((entry) => entry?.platform === "folders");
    const images = mine
      .filter((entry) => /^image\./.test(entry.entity_id) && !entry.hidden)
      .map((entry) => entry.entity_id);
    const sensor = mine.find((entry) => /^sensor\./.test(entry.entity_id))?.entity_id;
    const used = [language, ...[...images, sensor].map((id) => id && hass.states[id])];
    if (this._used?.length === used.length && used.every((item, index) => item === this._used[index])) return;
    this._used = used;
    const name = (state) => text(state.attributes.store) || text(state.attributes.friendly_name);
    const shown = images
      .map((id) => hass.states[id])
      .filter((state) => state && state.state !== "unavailable")
      .sort((a, b) => name(a).localeCompare(name(b), language));
    const tile = (state) => {
      const { entity_picture: picture, other_folders: others, valid_from: from, valid_until: until } = state.attributes;
      const local = typeof picture === "string" && /^\/api\//.test(picture);
      return el(
        "button",
        { className: "tile", type: "button", onclick: () => open(state.attributes.url) },
        el("img", local ? { src: picture, alt: "", loading: "lazy" } : { alt: "" }),
        line("name", name(state)),
        line("", text(state.attributes.folder)),
        line("small", period(hass, language, t, from, until)),
        line("small", Array.isArray(others) && others.length ? `+${others.length} ${t.more}` : ""),
      );
    };
    const offers = sensor && hass.states[sensor]?.attributes.offers;
    const lines = (Array.isArray(offers) ? offers : []).filter((offer) => offer && typeof offer === "object");
    const offer = (item) =>
      el("button", { type: "button", textContent: offerLine(t, language, item), onclick: () => open(item.url) });
    this._size = 1 + 7 * Math.ceil(shown.length / 2) + Math.ceil(lines.length / 2);
    const content =
      shown.length || lines.length
        ? [
            shown.length && el("div", { className: "grid" }, ...shown.map(tile)),
            lines.length && el("div", { className: "offers" }, ...lines.map(offer)),
          ]
        : [el("div", { className: "text", textContent: images.length ? t.empty : t.none })];
    this.shadowRoot.replaceChildren(el("style", { textContent: STYLE }), el("ha-card", {}, ...content));
  }

  _start() {
    if (this._config?.view !== "map" || !this.isConnected || this._timer) return;
    this._timer = setInterval(() => this._tick(), 1000);
    if (!this._map && !this._token) this._build();
  }

  _stop() {
    clearInterval(this._timer);
    clearTimeout(this._again);
    this._timer = this._again = this._seen = this._token = undefined;
    this._ready?.(false);
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
    this._footer = el("div", { className: "footer", textContent: t.footer });
    const area = el("div", { className: "map" }, map, this._hint);
    area.addEventListener("context-request", (ev) => this._provide(ev));
    area.addEventListener("hass-more-info", (ev) => {
      const id = ev.detail?.entityId;
      if (typeof id === "string" && Object.hasOwn(this._shops, id)) {
        ev.stopPropagation();
        this._open(id);
      }
    });
    area.addEventListener("map-clicked", () => {
      this._panel.hidden = true;
    });
    this._map = map;
    this.shadowRoot.replaceChildren(style, el("ha-card", {}, area, this._panel, this._footer));
    this._sync();
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
    this._footer.textContent = this._texts().t.footer;
  }

  _view() {
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
    const view = this._view();
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
    const asked = (this._asked = (this._asked || 0) + 1);
    const { t } = this._texts();
    if (view.zoom < 11) {
      this._show([], {});
      this._say(t.zoom);
      return;
    }
    const box = this._box(view);
    if (!box) return;
    let answer = null;
    try {
      answer = await this._hass.callWS({ type: "folders/shops", ...box });
    } catch {
      answer = null;
    }
    if (asked !== this._asked || !this._timer) return;
    const status = answer?.status;
    const ok = status === "ok";
    this._show(ok ? answer.shops : [], ok ? answer.stores : {});
    if (ok) this._say(answer.more ? t.all : "");
    else this._say(status === "zoom" ? t.zoom : status === "loading" ? t.loading : t.unavailable);
    const soon = !answer || status === "loading" || status === "not_loaded";
    this._again = setTimeout(() => this._ask(this._last), soon ? 15000 : HALF_HOUR);
  }

  _say(message) {
    this._hint.textContent = message;
    this._hint.hidden = !message;
  }

  _keep(value) {
    if (typeof value !== "string" || !value.startsWith(IMAGES)) return undefined;
    const base = value.split("?")[0];
    const kept = this._paths.get(base);
    if (kept && Date.now() - kept.at < HALF_HOUR) return kept.path;
    this._paths.set(base, { path: value, at: Date.now() });
    return value;
  }

  _show(shops, stores) {
    const entries = {};
    for (const shop of Array.isArray(shops) ? shops : []) {
      const store = stores && typeof stores === "object" ? stores[shop?.store] : undefined;
      const valid = /^[nwr]\d{1,15}$/.test(shop?.id) && Number.isFinite(shop.lat) && Number.isFinite(shop.lon);
      if (valid && store && typeof store === "object") {
        entries[`geo_location.folders_${shop.id}`] = { shop, store, logo: this._keep(store.logo) };
      }
    }
    const key = JSON.stringify(
      Object.entries(entries).map(([id, { shop, store, logo }]) => [id, shop.lat, shop.lon, text(store.name), logo]),
    );
    this._shops = entries;
    if (key !== this._drawn) {
      this._drawn = key;
      this._sync();
    }
  }

  _open(id) {
    const { shop, store } = this._shops[id];
    const { language, t } = this._texts();
    const folder = store.folder && typeof store.folder === "object" ? store.folder : null;
    const cover = folder && this._keep(folder.cover);
    const own = typeof folder?.url === "string" && folder.url.startsWith(SITE);
    const button = (label, action) => el("button", { type: "button", textContent: label, onclick: action });
    this._panel.replaceChildren(
      cover ? el("img", { src: cover, alt: "" }) : el("div"),
      el(
        "div",
        {},
        line("name", text(store.name)),
        line("small", text(shop.address)),
        folder && line("", text(folder.name)),
        folder && line("small", period(this._hass, language, t, folder.valid_from, folder.valid_until)),
        el(
          "div",
          { className: "actions" },
          button(own ? t.open : t.store, () => open(own ? folder.url : store.url)),
          button(t.close, () => {
            this._panel.hidden = true;
          }),
        ),
      ),
    );
    this._panel.hidden = false;
    (this._map.panTo ? this._map : this._map.leafletMap)?.panTo([shop.lat, shop.lon]);
  }
}

if (!customElements.get("folders-card")) {
  customElements.define("folders-card", FoldersCard);
  (window.customCards = window.customCards || []).push({
    type: "folders-card",
    name: "Folders",
    description: "The current folders and offers of the stores you follow, or a map of the shops in view.",
  });
}
