# Kaddio for Home Assistant

Let your Kaddio calendar run your rooms. When a client is booked in a room, the lights come on a few minutes
before and go off a few minutes after. The same signal can warm up the room, switch a "meeting in progress" sign,
or anything else Home Assistant can control.

It works per room: connect "Konferensrummet", "Behandlingsrum 1" and so on, each with its own timing.

## What you need

- **Home Assistant** version 2024.12 or newer, with [HACS](https://hacs.xyz) installed.
- **A Kaddio account with administrator rights**, at an organization that has the **API** module.
- Something in the room that Home Assistant can control: a smart plug, a light, a thermostat.

## Step 1: Enable the integration in Home Assistant

1. In Home Assistant, open **HACS**.
2. Click the menu (⋮) in the top right and choose **Custom repositories**.
3. Paste `https://github.com/kaddio/homeassistant-kaddio`, set the type to **Integration**, and click **Add**.
4. Search for **Kaddio** in HACS, open it, and click **Download**.
5. **Restart Home Assistant** (Settings → System → Restart).

> Once Kaddio is listed in the official HACS store, steps 2 and 3 are no longer needed: just search for Kaddio.

## Step 2: Create an API key in Kaddio

1. In Kaddio, go to **Inställningar → API**.
2. Click **Ny API-nyckel** and name it, for example `Home Assistant`.
3. Under **Tillåtna GraphQL-endpoints**, select only these three, so the key can do nothing else:
   `findEventsIndexed`, `findRooms` and `findPlaces`.
4. Click **Skapa nyckel** and **copy the key**. It is shown only once.

You can revoke the key at any time on the same page (**Återkalla**).

## Step 3: Connect a room

1. In Home Assistant, go to **Settings → Devices & services → Add integration** and search for **Kaddio**.
2. Enter your Kaddio address (for example `myclinic.kaddio.com`) and paste the API key.
3. Choose the **room** (a *Rum* in Kaddio's settings). You can also choose a *Plats*, or everything.
4. Give it a name, for example the room's name.

Repeat for each room you want to automate. Each room gets:

| Entity | What it tells you |
| --- | --- |
| **Calendar** | The room's bookings and activities, visible in Home Assistant's calendar. |
| **Busy** (*Upptagen*) | **On** from a few minutes before a booking starts until a few minutes after it ends. |

## Step 4: Tune what counts and when

Open the integration, click the gear icon next to the room, and set:

- **What counts as busy:** client meetings and group sessions by default. Tick *Calendar entries*
  (*Kalenderposter*) to include activities too, such as a cleaning block.
- **Minutes before start / after end:** how early the room switches on and how long it stays on.
  Back-to-back bookings keep the room on without switching off in between.

## Step 5: Control something

1. Go to **Settings → Automations & scenes → Create automation → Create new automation**.
2. **When:** add *State*, pick the room's **Busy** sensor, and set it to **on**.
3. **Then do:** add the action to turn on your light or switch, and pick it from the list.
4. Create a second automation the same way: Busy sensor **off** → turn the light or switch **off**.

Prefer one automation? Open its ⋮ menu → **Edit in YAML** and paste this, replacing the two entity IDs with
yours (smart plugs are `switch.…`; for lights use `light.turn_on` / `light.turn_off`):

```yaml
alias: Kaddio - room follows bookings
mode: restart
triggers:
  - trigger: state
    entity_id: binary_sensor.kaddio_busy
    to: "on"
    id: "on"
  - trigger: state
    entity_id: binary_sensor.kaddio_busy
    to: "off"
    id: "off"
actions:
  - choose:
      - conditions:
          - condition: trigger
            id: "on"
        sequence:
          - action: switch.turn_on
            target:
              entity_id: switch.treatment_room_lamp
    default:
      - action: switch.turn_off
        target:
          entity_id: switch.treatment_room_lamp
```

### Heating before the meeting

Heating needs more time than a lamp. Use the room's **Calendar** with Home Assistant's *Calendar* trigger
(*Event: start*, offset `-0:30:00`) to start 30 minutes early. A ready-made blueprint is in
`blueprints/automation/kaddio/room_prep.yaml` (import it under Settings → Automations & scenes → Blueprints).

## How it works, and its limits

- Kaddio is checked **every 15 minutes**. A new, moved or cancelled booking can take up to 15 minutes to be noticed.
  To refresh at once: Devices & services → Kaddio → ⋮ → **Reload**.
- Only **bookings, group sessions and calendar entries** that have the room selected are used. Events without a
  room are not seen when you connect a single room.
- It reads from 1 day back to 60 days ahead.

## Privacy and security

- Only times, the booking type name and (for activities) the title and note are read. **No client names, journal
  notes, prices or invoices are ever requested.**
- The API key is stored in Home Assistant. Use a key dedicated to Home Assistant, limited to the three endpoints
  above, and revoke it in Kaddio if you stop using the integration.

## Troubleshooting

| Problem | What to check |
| --- | --- |
| "Kaddio refused the token" when connecting | The key must be created by an administrator at an organization with the API module, and the three endpoints must be allowed. |
| The room list is empty | The organization has no rooms or places set up in Kaddio. |
| A booking doesn't show up | It must have this room selected, and may need up to 15 minutes, or reload the integration. |
| An activity doesn't turn the Busy sensor on | Tick *Calendar entries* in the integration's options. |
| Nothing happens in the room | Check the Busy sensor first, then the automation's trace (*Show trace*), then try the light or plug by hand. |

Logs: Settings → System → Logs, search for `kaddio`. Report problems at
[github.com/kaddio/homeassistant-kaddio/issues](https://github.com/kaddio/homeassistant-kaddio/issues).

## License and trademarks

The code is MIT licensed. The Kaddio name and logos are trademarks of Kaddio AB and are not covered by the MIT
license.

For developers, see [DEVELOPMENT.md](DEVELOPMENT.md).
