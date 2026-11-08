# Development

## Layout

- `custom_components/kaddio/` – the integration.
  - `gql.py`, `schedule.py`, `models.py` – no Home Assistant imports, unit tested on their own.
  - `coordinator.py` – polls the Kaddio GraphQL API every 15 minutes.
  - `calendar.py`, `binary_sensor.py`, `config_flow.py` – Home Assistant platforms and setup.
- `brand/` – logo vectors. `scripts/build_brand.sh` regenerates the PNGs in `custom_components/kaddio/brand/`
  (needs `rsvg-convert`).
- `blueprints/` – optional automation blueprint (not installed by HACS).

## What is requested from Kaddio

`findRooms` and `findPlaces` (id, name, deleted) during setup, and `findEventsIndexed(start, end, locationId)` for
`booking`, `session` and `cal` events: start, end, type, title, calendar note and the booking type name. Admin API key
required; the organization needs the API module.

## Tests

```
python3 -m unittest discover -s tests
```

CI also runs hassfest and the HACS action.

## Releasing

1. Bump `version` in `custom_components/kaddio/manifest.json` and push to `main`.
2. Tag and push: `git tag v<version> && git push origin v<version>`.

The *Release* workflow checks that the tag matches the manifest version, runs the tests and publishes the GitHub
release with generated notes. HACS then offers it as an update.

## Publishing to the catalog (HACS / Marketplace)

Home Assistant 2026.11 and newer ship HACS built in as the Marketplace. Getting into the catalog works the same
as before ([guide](https://contributors.home-assistant.io/marketplace/guides/catalog/)):

1. Repo is public with a description, topics, issues enabled and a README. (Done)
2. The HACS action and hassfest both pass, with no `ignore`. (Done, see `.github/workflows/validate.yml`)
3. At least one full GitHub release exists, not only a tag. (Done, created by the Release workflow)
4. Fork `hacs/default`, branch from `master`, and add `kaddio/homeassistant-kaddio` to the `integration` file in
   alphabetical order.
5. Open the PR from a **personal GitHub account** (the one in `codeowners`), not from the organization. Fill in the
   PR template, with links to the latest release and to passing HACS action and hassfest runs.
6. Review can take months. Meanwhile users can install from the link in the README.

The Marketplace also refuses to install a repository without `hacs.json` in the root, with an invalid domain, or with
a manifest whose `version` the loader rejects ([validation checks](https://contributors.home-assistant.io/marketplace/reference/validation/)).
Optional extras the HACS action looks at: images in the README and `categories` in the manifest.

