# Security policy

Folders-HA has no accounts and handles no personal data beyond the stores you follow and your watch words. Security and privacy problems are still taken seriously.

## Reporting a vulnerability

Do **not** open a public issue for security or privacy problems. Report them privately through [GitHub private vulnerability reporting](https://github.com/Paulus1337/Folders-HA/security/advisories/new).

Please include the version, what you observed and how to reproduce it.

## Scope

In scope:

- Any request to folders.nl, OpenStreetMap or another service that is not documented in the README, or a location that Folders sends anywhere.
- Data that leaves Home Assistant beyond what the README describes, for example the watch words or store names in diagnostics or logs.
- Text, links or images from folders.nl or OpenStreetMap that the Folders card turns into HTML or script, or links it opens outside folders.nl.
- The image view (`/api/folders/image/...`): images from other addresses than the folders.nl data, access without a signed-in user or a valid signed path, or file types other than JPEG, PNG, WebP and GIF.

Out of scope: problems in folders.nl, OpenStreetMap or Home Assistant itself. Report those to them.

## Supported versions

Only the latest release receives fixes.
