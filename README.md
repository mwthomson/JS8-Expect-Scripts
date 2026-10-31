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
  `js8spotter.db.bak-YYYYMMDD` next to the original. It keeps the 7 newest
  backups and deletes older ones.
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

## quake2expect.py

Keeps a JS8Spotter Expect reply updated with recent earthquakes near your
grid square, from the public [USGS earthquake feed](https://earthquake.usgs.gov/fdsnws/event/1/).
No API key is needed. Callers send `YOURCALL E? QUAKE`.

Example replies:

```
QUAKE 1415L 24H 3 MAX M3.1 28MI NE 0412L
QUAKE 1415L 24H NONE M2.5+ 100MI
```

| Field | Meaning |
|-------|---------|
| `1415L` | When the reply was last updated, local. An old time means the feed or script is down |
| `24H` | Time window searched |
| `3` | Number of quakes in the window at or above the minimum magnitude |
| `MAX M3.1` | Magnitude of the largest one |
| `28MI NE` | Its distance and direction from the center of your grid square |
| `0412L` | Its time, local |

It uses the same database update and daily backup as `ambient2expect.py`,
so keep both scripts in the same folder.

### Setup

1. **Create the Expect entry in JS8Spotter** with the trigger `QUAKE` and
   any placeholder reply, as in step 3 for `ambient2expect.py` above.

2. **Preview the reply:**

   ```bash
   python3 quake2expect.py --grid DN43AP --dry-run
   ```

   Options:
   - `--radius 100` sets the search radius in miles.
   - `--hours 24` sets the time window.
   - `--min-mag 2.5` sets the smallest magnitude counted.
   - `--trigger XX` updates a different Expect trigger. The default is `QUAKE`.

3. **Update for real:**

   ```bash
   python3 quake2expect.py --grid DN43AP --db ~/js8spotter/js8spotter.db \
       --table expect --key-col expect --resp-col reply
   ```

4. **Schedule it every 15 minutes** with `crontab -e`:

   ```
   */15 * * * * python3 $HOME/Projects/JS8-Expect-Scripts/quake2expect.py --grid DN43AP --db $HOME/js8spotter/js8spotter.db --table expect --key-col expect --resp-col reply >> $HOME/.cache/quake2expect.log 2>&1
   ```

To check the distance and grid math, run `python3 test_quake2expect.py`.
To check backup cleanup, run `python3 test_ambient2expect.py`. Each should
print `ok`.
