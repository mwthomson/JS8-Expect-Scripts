# JS8-Expect-Scripts
Scripts for use with JS8Spotter's Expect system

## ambient2expect.py

Keeps a JS8Spotter Expect reply updated with live conditions from an
[Ambient Weather](https://ambientweather.net) station. Anyone allowed by the
entry can send `YOURCALL E? WX` over JS8Call and get current weather back.

Example reply:

```
WX 1619L 48F RH62 NW8G15 B30.02 R0.12 R24H0.30
```

| Field | Meaning |
|-------|---------|
| `1619L` | Time of the station reading, local |
| `48F` | Outdoor temperature, °F |
| `RH62` | Relative humidity, % |
| `NW8G15` | Wind direction, speed and gust, mph (`CALM` if 0) |
| `B30.02` | Relative barometric pressure, inHg |
| `R0.12` | Rain today, inches (only shown when > 0) |
| `R24H0.30` | Rain in the last 24 hours, inches (only shown when > 0) |
| `STALE` | Added when the reading is more than 30 minutes old |

The script fetches the latest reading from the Ambient Weather API and
writes it into the reply of one Expect row in `js8spotter.db`. It uses only
the Python 3 standard library.

Safety:
- Once a day, before writing, it backs up the database to
  `js8spotter.db.bak-YYYYMMDD` next to the original.
- It changes nothing unless exactly one Expect row matches the trigger.

### Setup

1. **Get API keys.** At ambientweather.net, open Account > API Keys and
   create an API Key and an Application Key.

2. **Store the keys** in a file only you can read. Don't commit it.

   ```bash
   install -m 600 /dev/null ~/.config/ambient.env
   ```

   Then put this in `~/.config/ambient.env`, using your own keys:

   ```
   AMBIENT_APP_KEY=your_application_key
   AMBIENT_API_KEY=your_api_key
   # AMBIENT_MAC=00:0E:C6:XX:XX:XX   # only if your account has more than one station
   ```

3. **Create the Expect entry in JS8Spotter.** Use the trigger `WX` and any
   placeholder reply. Set the Allowed list (`*` lets anyone use it), and set
   Max replies to 99 for unlimited.

   In JS8Call, turn on Autoreply. Also uncheck "Allow sending standard
   messages without callsign", or `E?` requests won't work.

4. **Check the database layout** (read-only):

   ```bash
   python3 ambient2expect.py --db ~/js8spotter/js8spotter.db --inspect
   ```

   In current JS8Spotter versions, the table is `expect`, with trigger column
   `expect` and reply column `reply`.

5. **Preview the reply** without touching the database:

   ```bash
   set -a; . ~/.config/ambient.env; set +a
   python3 ambient2expect.py --dry-run
   ```

6. **Update for real:**

   ```bash
   python3 ambient2expect.py --db ~/js8spotter/js8spotter.db \
       --table expect --key-col expect --resp-col reply
   ```

   Options:
   - `--trigger XX` updates a different Expect trigger. The default is `WX`.
   - `--grid DN43` adds your grid square to the reply.

7. **Schedule it every 15 minutes** with `crontab -e`:

   ```
   */15 * * * * set -a; . $HOME/.config/ambient.env; python3 $HOME/Projects/JS8-Expect-Scripts/ambient2expect.py --db $HOME/js8spotter/js8spotter.db --table expect --key-col expect --resp-col reply >> $HOME/.cache/ambient2expect.log 2>&1
   ```

   On Windows, use Task Scheduler with the same command, and set the two
   keys as user environment variables.

### Notes
- Keep the reply short. Every character costs airtime.
