<p align="center">
  <img src="https://raw.githubusercontent.com/Paulus1337/Folders-HA/main/custom_components/folders/brand/icon@2x.png" alt="Folders-HA icon" width="128">
</p>

<h1 align="center">Folders-HA</h1>

<p align="center">
  <strong>Folders for Home Assistant</strong><br>
  The weekly folders of Dutch stores, your offers and a map of the shops near you, in Home Assistant.
</p>

<p align="center">
  <a href="https://github.com/Paulus1337/Folders-HA/releases"><img src="https://img.shields.io/github/v/release/Paulus1337/Folders-HA?style=flat-square" alt="Release"></a>
  <a href="https://hacs.xyz"><img src="https://img.shields.io/badge/HACS-Custom-41BDF5?style=flat-square" alt="HACS custom repository"></a>
  <img src="https://img.shields.io/badge/Home%20Assistant-2025.8%2B-41BDF5?style=flat-square&logo=homeassistant&logoColor=white" alt="Home Assistant 2025.8 or newer">
  <a href="https://github.com/Paulus1337/Folders-HA/actions/workflows/validate.yml"><img src="https://img.shields.io/github/actions/workflow/status/Paulus1337/Folders-HA/validate.yml?branch=main&style=flat-square&label=validate" alt="Validate"></a>
  <a href="LICENSE"><img src="https://img.shields.io/github/license/Paulus1337/Folders-HA?style=flat-square" alt="License: MIT"></a>
</p>

> [!IMPORTANT]
> **Unofficial open-source hobby project.** Folders-HA is made by volunteers in their spare time. It is not made, endorsed or supported by folders.nl, Publitas, WePublish or any store. It uses the same API as the folders.nl website, which can change at any time. Please do not contact folders.nl or the stores about it; use the [issue tracker](https://github.com/Paulus1337/Folders-HA/issues) instead.

## Features

- **Your stores**: follow up to 60 stores from the list of folders.nl. Each one gets an image entity with its current folder, or the next one when there is none yet.
- **Folders dashboard**: one card that shows the current folder of every store you follow, with a link to open it on folders.nl.
- **Offers**: up to 10 watch words, such as *koffie* or *luiers*. The offers of your stores that match a word are listed in a sensor and on the dashboard.
- **Notifications**: an event for every new folder of your stores and every new matching offer.
- **Map**: Home Assistant's own map, with the shops of the Netherlands that have a folder. Scroll and zoom anywhere; the shops in view load with their store logos, and clicking a shop shows its folder.
- **Privacy first**: Folders itself never sends a location; the map tiles come from the provider of Home Assistant's own map, as on every map in Home Assistant. See [Privacy and security](#privacy-and-security).
- **English and Dutch**.

## Requirements

- Home Assistant 2025.8 or newer.
- No account is needed. folders.nl only covers stores in the Netherlands.

## Quick start

1. Add this repository (`https://github.com/Paulus1337/Folders-HA`) to the Marketplace or HACS and install **Folders**. Restart Home Assistant if it asks you to.
2. Go to **Settings > Devices & services > Add integration > Folders**, choose your stores and, if you like, some watch words.
3. Add the Folders card to a dashboard (see [The folders dashboard and the map](#the-folders-dashboard-and-the-map)), or use the [example dashboard](examples/dashboard.yaml) with both views.
4. Optional: get a notification for every new folder, as described under [Notifications](#notifications).

## Installation

### Marketplace or HACS (recommended)

[![Open your Home Assistant instance and add this repository to the Marketplace or HACS.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Paulus1337&repository=Folders-HA&category=integration)

1. Click the button above. It opens the Marketplace (Home Assistant 2026.11 and newer) or HACS (older versions). You can also add `https://github.com/Paulus1337/Folders-HA` as a custom repository of type **Integration**.
2. Install **Folders**. Restart Home Assistant if it asks you to.

### Manual

1. Copy `custom_components/folders` into the `custom_components` folder of your Home Assistant configuration.
2. Restart Home Assistant.

## Setup and options

[![Open your Home Assistant instance and start setting up Folders.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=folders)

1. Go to **Settings > Devices & services > Add integration > Folders**. Home Assistant loads the list of stores from folders.nl.
2. Under **Stores**, choose the stores you follow (at most 60). Under **Watch words**, type up to 10 words, separated by commas, for example `koffie, kaas, luiers`. Words are matched by the search of folders.nl, so use Dutch product words. Both fields are optional.
3. Select **Submit**.

Folders can be added once. To change the stores or the watch words later, go to **Settings > Devices & services > Folders** and select **Configure** (the cogwheel). Saving reloads the integration. When you stop following a store, its image entity is removed.

| Option | Default | What it does |
| --- | --- | --- |
| Stores | None | The stores you follow. Each one gets an image entity, and only their offers count. |
| Watch words | None | Up to 10 words of 2 to 40 characters. Upper case, extra spaces and duplicates do not matter. |

## The folders dashboard and the map

The integration makes the **Folders card** available on every dashboard. In the dashboard editor, select **Add card** and pick **Folders**, or add it in YAML.

The folders dashboard (the default view) shows a tile for every store you follow that has a folder, sorted by store: the first page of the folder, the store, the name of the folder and until when it is valid, or from when for a folder that has not started yet. "+2 more" means the store has more current or coming folders; they are listed in the attributes of its image entity. Select a tile to open the folder on folders.nl in a new tab. Below the tiles are the offers that match your watch words, such as "Albert Heijn: Koffiebonen, 4.99 (was 6.49)"; select one to open its folder.

```yaml
type: custom:folders-card
```

The map is Home Assistant's own map, so it looks and behaves like every other map in Home Assistant, in light and dark mode. It starts at your home. Scroll and zoom anywhere in the Netherlands: from zoom level 11, the shops in view that have a current or coming folder appear with their store logo, at most 300 at a time, nearest to the centre first. Select a shop to see its address and folder under the map, with a button that opens the folder on folders.nl. The first time anyone opens the map, Home Assistant downloads the shops of the whole country, which takes a few minutes; the map says so meanwhile.

```yaml
type: custom:folders-card
view: map
zoom: 14
```

| Option | Default | What it does |
| --- | --- | --- |
| `view` | `folders` | `folders` for the folders dashboard, `map` for the map. |
| `zoom` | `14` | The zoom level the map starts at (1 to 20). Shops show from zoom level 11. |

The map works best in a panel view, which gives it the whole screen. In a sections view it takes the full width.

If the card is missing right after installing or updating Folders-HA, reload the page or restart the Home Assistant app.

### Example dashboard

[`examples/dashboard.yaml`](examples/dashboard.yaml) is a dashboard with two views: **Folders** with the folders dashboard, and **Map** with the map in a panel view. Go to **Settings > Dashboards > Add dashboard > New dashboard from scratch** and open the dashboard. Select **Edit dashboard** (the pencil at the top, or in the three-dot menu on a narrow screen), then open the three-dot menu and select **Raw configuration editor**. Replace the text with the content of the file and save.

## Notifications

A phone notification for every new folder of a store you follow. Go to **Settings > Automations & scenes > Create automation > Create new automation**, open the three-dot menu, select **Edit in YAML**, replace the text with this and save:

```yaml
alias: "Folders: new folder"
mode: queued
triggers:
  - trigger: state
    entity_id: event.folders_folders
conditions:
  - "{{ trigger.from_state and trigger.to_state and 'unavailable' not in (trigger.from_state.state, trigger.to_state.state) }}"
  - "{{ trigger.to_state.attributes.event_type == 'new_folder' }}"
actions:
  - action: notify.mobile_app_your_phone
    data:
      title: "New folder: {{ trigger.to_state.attributes.store }}"
      message: "{{ trigger.to_state.attributes.folder or 'Folder' }}, from {{ as_timestamp(trigger.to_state.attributes.valid_from) | timestamp_custom('%a %-d %b') }}"
      data:
        url: "{{ trigger.to_state.attributes.url }}"
        clickAction: "{{ trigger.to_state.attributes.url }}"
```

- Replace `notify.mobile_app_your_phone` with the notify action of your own phone. Do not use `notify.notify`: it sends to every phone with the Home Assistant app.
- For new offers, use `new_offer` in the second condition, and `title`, `price`, `sale_price` and `word` in the message.
- Keep the first condition and `mode: queued`: one update can bring several events, and a restart briefly makes the event entity unavailable.
- Selecting the notification opens the folder on folders.nl.

## Entities

The integration creates one **Folders** service device with these entities.

| Entity ID | Dutch entity ID | Description |
| --- | --- | --- |
| `image.folders_<store>` | the same | One for every store you follow, for example `image.folders_albert_heijn`. The first page of the shown folder; unavailable while the store has no folder. Attributes: `store`, `folder`, `valid_from`, `valid_until`, `upcoming` (true when the folder has not started yet), `url` (the folder on folders.nl), `store_url` and `other_folders` (up to 5 other current or coming folders, each with `name`, `valid_from`, `valid_until` and `url`). The state is the time Home Assistant last saw the shown folder change. It also changes when Home Assistant starts or the integration reloads, so use `event.folders_folders` for notifications. |
| `sensor.folders_offers` | `sensor.folders_aanbiedingen` | The number of current offers of the stores you follow that match a watch word. Attributes: `words` and `offers` (up to 50, sorted by store and title, each with `store`, `title`, `price`, `sale_price`, `valid_until`, `url` and `page`). |
| `event.folders_folders` | `event.folders_folders` | Fires `new_folder` with `store`, `folder`, `valid_from`, `valid_until` and `url`, and `new_offer` with `store`, `title`, `price`, `sale_price`, `word` and `url`. |

The shown folder of a store is the current folder that started last; when no folder is current, the next one. A price of `null` means folders.nl gives no price. `page` is the page number of the offer as folders.nl gives it.

Home Assistant creates the entity IDs once, in its own language (**Settings > System > General**): Dutch IDs when Home Assistant is set to Dutch, English IDs in every other language. Use your own entity IDs wherever this README shows one.

## Privacy and security

- **Folders never sends a location.** Not to folders.nl, not to the OpenStreetMap Overpass API.
- **folders.nl only gets general questions**: the list of stores, all current and coming folders, and one search per watch word. Your watch words are sent as search terms. There is no account and no sign-in. When they are shown, Home Assistant also downloads the first page of the shown folder of each store you follow, and the logos and covers of the stores on the map, from the WePublish image hosts of folders.nl. These requests name a folder or a store, never a location or a watch word.
- **The OpenStreetMap Overpass API only gets the store names.** The map needs the shops of the stores, and Home Assistant gets them in one download for the whole country: the question names all folders.nl stores and the Netherlands, never a place. This only happens when the map is used: the first time, and after that when the list is older than 14 days (after a failed download, an hour later at the earliest).
- **Apart from the map tiles, your browser only talks to Home Assistant.** The folder pages go through Home Assistant's image proxy, and the store logos and folder covers on the map are served by Home Assistant itself, so your browser never contacts folders.nl. Links to folders.nl only open when you select them, in a new tab without a referrer.
- **Map tiles**: the map is Home Assistant's own map. It starts at your home and loads the tiles of the area on screen from its map provider: newer versions of Home Assistant get them through Home Assistant itself from the OpenStreetMap tile servers, older versions load them directly in your browser from CARTO. That provider sees which area you look at, as with every map in Home Assistant.
- **Nothing personal is stored.** The Folders entry keeps the stores you follow and your watch words. The shop list in `.storage/folders.shops` is public OpenStreetMap data with the time of the download. The `other_folders` and `offers` attributes are left out of the history.
- **Safe diagnostics.** The Folders part of the diagnostics only contains counts: followed stores, watch words, stores, folders, offers, image entities and shops, the age of the shop list and whether the last update worked. Never the words or store names. Home Assistant adds its own details, such as its version and the list of installed custom integrations, so look the file over before you share it.
- **No extra packages.** The integration only uses libraries that come with Home Assistant. Requests to folders.nl use Home Assistant's own connection, whose user agent names Home Assistant. The OpenStreetMap download names this integration instead (`Folders-HA` with a link to this page), because the OpenStreetMap server refuses general programming library names.

Anyone who can open your Home Assistant can see the Folders entities and use the map. To report a security problem, see the [security policy](SECURITY.md).

## Known limitations

- Shops come from OpenStreetMap, which volunteers keep up to date. Shops can be missing, closed or in the wrong place.
- Shops are matched to stores by name: the brand of a shop in OpenStreetMap, or else its name, must be the name of the store on folders.nl (case, accents, spaces and punctuation do not matter). Shops with another name do not show, and a shop with the same name as a store can show by mistake.
- folders.nl gives offers a title and prices, but no discount percentages.
- Only Dutch stores. folders.nl has no folders for other countries.
- The first map load takes a few minutes, because it downloads the shops of the whole country.
- The public OpenStreetMap server is sometimes busy. Home Assistant then tries twice more, and after that again after an hour at the earliest.
- The map shows at most 300 shops at a time and only shops of stores that have a current or coming folder.
- Which folders and offers were already seen is not kept over restarts. After a restart, reload or options change, the first update only remembers what exists, so nothing fires for what appeared meanwhile.
- Repositories added from a link are checked for updates by the Marketplace every 48 hours, and only when Home Assistant is connected to GitHub.

## Troubleshooting

- **"Could not reach folders.nl" during setup**: check that Home Assistant has internet access and try again later. Submitting the form again tries again.
- **The map says "Loading the shops of the Netherlands"**: the first download takes a few minutes. The card asks again every 15 seconds.
- **The map says "Shops are not available right now"**: the download failed, usually because the public OpenStreetMap server is busy. Home Assistant tries again an hour later, when the map asks for shops. The log says what happened.
- **The map says "Zoom in to see the shops"**: shops show from zoom level 11, in a view of at most 1.5 degrees.
- **The map says "The map could not be loaded"**: reload the page. The card uses the map of Home Assistant itself, which loads with it.
- **Debug logging**: add the following to `configuration.yaml`, or to its `logger:` section if it already has one.

  ```yaml
  logger:
    logs:
      custom_components.folders: debug
  ```

## Removal

1. Remove the Folders card from your dashboards, and delete a dashboard made from the example in **Settings > Dashboards**; without the integration they show errors.
2. Delete the Folders entry in **Settings > Devices & services**. This also deletes the stored shop list.
3. Remove the integration in the Marketplace or HACS, or delete `custom_components/folders`.
4. Restart Home Assistant.

## How it works

This section documents the design, so the code itself can stay small.

### folders.nl

Every 3 hours Home Assistant asks folders.nl, through the GraphQL API its website uses (`api.wepublish.digital`), for the list of stores (at most once a day), for all current and coming folders of all stores (the map needs every store, the dashboard only yours) and, per watch word, for the matching offers. Lists are read in pages of 100: at most 10 pages of stores and folders, and 3 pages per word. Each request waits at most 30 seconds. A store list without any store counts as a failed update. After a failed update, the next try is 15 minutes later instead of 3 hours. Only `https` images from the WePublish hosts are used, and only `folders.nl` links.

### The shop list

The first time the map asks for shops, Home Assistant downloads the shops of all folders.nl stores in the Netherlands from the public OpenStreetMap Overpass API in one request, which takes about two minutes and is about 4 MB. A busy server is asked again after 30 and after 90 seconds. An answer without any shop of a folders.nl store counts as a failed download. Home Assistant keeps the shops (an id, the place rounded to about a metre, the store, the street, the house number and the town) in `.storage/folders.shops`, so a restart does not download them again. After 14 days the list is downloaded again in the background while the old one keeps serving. After a failed download, the next try is an hour later at the earliest.

### The map

The Folders card checks once per second which part of the map is in view, while the page is visible. When the view stops changing, it asks Home Assistant for the shops in that box, and Home Assistant answers from the stored list, without any request to the internet. The logos and covers come with paths that are signed for one hour, so the card asks again every 30 minutes. Home Assistant keeps at most 200 logos and covers, and at most 20 MB, in memory for 6 hours, and only accepts JPEG, PNG, WebP and GIF images of at most 2 MB.

### Events

`event.folders_folders` fires once for every folder of a store you follow and every matching offer that appears after the entry was loaded, oldest start first. Folders of next week often appear a few days early, and fire then; their offers fire when the folder starts. The event entity stays available when folders.nl cannot be reached, so an outage never looks like a new event.

## Contributing

Contributions are welcome. Please open an issue first to discuss the change.

The code has no comments on purpose: this README is the documentation. Every push is checked by hassfest and the HACS action, in a workflow that can only read this repository and has no secrets.

## License and trademarks

Folders-HA is released under the [MIT license](LICENSE). It is an unofficial hobby project and is not made, endorsed or sponsored by folders.nl, Publitas, WePublish or any store. Store names and logos are trademarks of their owners. Shop data (c) OpenStreetMap contributors, available under the Open Database License (ODbL).
