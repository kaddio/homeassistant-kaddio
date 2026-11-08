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
