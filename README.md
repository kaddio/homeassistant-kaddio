# Kaddio for Home Assistant

Use your [Kaddio](https://kaddio.com) calendar to control your home or clinic:
lights on before a session, off after it, "do not disturb" signs, heating, and so on.

The integration uses the Kaddio GraphQL API with an **administrator API token**, and creates one calendar per Kaddio room
(or place, or one for the whole organization). The organization needs the Kaddio API module. Only times, titles and booking type names are
requested; client data is never read.

## What you get

| Entity | Purpose |
| --- | --- |
| `calendar.<name>` | Client meetings, group sessions and calendar entries for a room. Works with Home Assistant's built-in **Calendar** automation trigger (event start/end with an offset). |
| `binary_sensor.<name>_busy` | On from *N* minutes before an entry starts until *N* minutes after it ends (configurable). Attributes: `current_summary`, `next_start`, `next_summary`. |

## Installation (HACS)

1. HACS → ⋮ → **Custom repositories** → add `https://github.com/kaddio/homeassistant-kaddio` as *Integration*
   (not needed once Kaddio is in the HACS default list).
2. Install **Kaddio**, restart Home Assistant.
3. Settings → Devices & services → **Add integration** → *Kaddio*.
4. Enter your Kaddio address (for example `https://myclinic.kaddio.com`) and an administrator API token.
5. Pick a room (a *Rum* in Kaddio's settings), a place (*Plats*), or everything.

Add the integration once per room you want to automate.

## Example: heat 30 min before, lights 5 min before, off 5 min after

Import the blueprint `blueprints/automation/kaddio/room_prep.yaml`, pick the room's calendar and busy sensor, your
lights and thermostat. Only **client meetings and group sessions** count as busy by
default (change under the integration's *Configure*), so a lunch block in the calendar does not heat the room.
Back-to-back meetings keep the lights on: they only go off when the gap is longer than lead + trail.

Prefer YAML? Any offset works with Home Assistant's calendar trigger:

```yaml
trigger:
  - platform: calendar
    event: start
    offset: "-0:30:00"       # heating: 30 min before
    entity_id: calendar.kaddio_room_1
action:
  - service: climate.set_temperature
    target: { entity_id: climate.room_1 }
    data: { temperature: 21 }
```

## Privacy and security

The API token is stored in Home Assistant and gives administrator access to the Kaddio API, so create a token
dedicated to Home Assistant and revoke it in Kaddio if it leaks; Home Assistant will then ask for a new one.
Only times, titles and booking type names are requested. The calendar is refreshed every 15 minutes and covers one
day back to 60 days ahead; the busy sensor changes state at exact times between refreshes.

## Development

```
python3 -m unittest discover -s tests
```

## Releasing

1. Bump `version` in `custom_components/kaddio/manifest.json` and push to `main`.
2. Tag and push: `git tag v<version> && git push origin v<version>`.

The *Release* workflow checks that the tag matches the manifest version, runs the tests and publishes the GitHub
release with generated notes. HACS then offers it as an update.

## License and trademarks

The code is MIT licensed. The Kaddio name and logos (`brand/`) are trademarks of Kaddio AB; the MIT license does not
grant rights to them. `scripts/build_brand.sh` regenerates the PNGs in `custom_components/kaddio/brand/` from the SVGs.
