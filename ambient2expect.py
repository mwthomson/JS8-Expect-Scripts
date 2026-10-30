#!/usr/bin/env python3
"""
ambient2expect.py - push current Ambient Weather conditions into a JS8Spotter
Expect response, so `YOURCALL E? WX` returns live data.

Stdlib only. Usage:
  1) Inspect the DB once to find the Expect table/columns:
       python3 ambient2expect.py --db /path/js8spotter.db --inspect
  2) Preview the string without touching the DB:
       python3 ambient2expect.py --dry-run
  3) Run for real (cron / Task Scheduler every 15 min):
       python3 ambient2expect.py --db /path/js8spotter.db \
           --table expect --key-col expect --resp-col reply

Keys come from env: AMBIENT_APP_KEY, AMBIENT_API_KEY (optional AMBIENT_MAC).
Make keys at ambientweather.net > Account > API Keys.
"""
import argparse
import json
import os
import sqlite3
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone

API = "https://rt.ambientweather.net/v1/devices"
DIRS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
STALE_MIN = 30


def fetch(app_key, api_key, mac=None):
    q = urllib.parse.urlencode({"applicationKey": app_key, "apiKey": api_key})
    req = urllib.request.Request(f"{API}?{q}", headers={"User-Agent": "ambient2expect"})
    with urllib.request.urlopen(req, timeout=20) as r:
        devs = json.load(r)
    if not devs:
        sys.exit("No devices on this Ambient account.")
    if mac:
        devs = [d for d in devs if d.get("macAddress", "").lower() == mac.lower()]
        if not devs:
            sys.exit(f"Device {mac} not found.")
    return devs[0]["lastData"]


def cardinal(deg):
    return DIRS[int((float(deg) % 360) / 45 + 0.5) % 8]


def fmt(d, grid=""):
    """Terse, JS8-safe (uppercase, no degree/percent signs).
    e.g. 'WX 1545L 48F RH62 NW8G15 B30.02 R0.12'"""
    parts = ["WX"]
    ts = d.get("dateutc")
    stale = False
    if ts:
        t = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
        stale = (datetime.now(timezone.utc) - t).total_seconds() > STALE_MIN * 60
        parts.append(t.astimezone().strftime("%H%M") + "L")
    if grid:
        parts.append(grid.upper())
    if "tempf" in d:
        parts.append(f"{round(d['tempf'])}F")
    if "humidity" in d:
        parts.append(f"RH{round(d['humidity'])}")
    if "windspeedmph" in d:
        ws = round(d["windspeedmph"])
        if ws == 0:
            parts.append("CALM")
        else:
            w = (cardinal(d["winddir"]) if "winddir" in d else "") + str(ws)
            g = round(d.get("windgustmph", 0))
            if g > ws:
                w += f"G{g}"
            parts.append(w)
    if "baromrelin" in d:
        parts.append(f"B{d['baromrelin']:.2f}")
    if d.get("dailyrainin", 0) > 0:
        parts.append(f"R{d['dailyrainin']:.2f}")
    if stale:
        parts.append("STALE")
    return " ".join(parts)


def inspect(db):
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    cur = con.cursor()
    tables = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    for t in tables:
        cols = [c[1] for c in cur.execute(f'PRAGMA table_info("{t}")')]
        n = cur.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
        flag = "  <-- likely Expect" if "expect" in t.lower() else ""
        print(f"{t} ({n} rows): {', '.join(cols)}{flag}")
        if flag:
            for row in cur.execute(f'SELECT * FROM "{t}" LIMIT 5'):
                print("    ", row)
    con.close()


def backup_daily(db):
    path = f"{db}.bak-{datetime.now():%Y%m%d}"
    if os.path.exists(path):
        return
    src = sqlite3.connect(db)
    dst = sqlite3.connect(path)
    src.backup(dst)  # safe while JS8Spotter has the DB open
    dst.close()
    src.close()


def update(db, table, key_col, resp_col, trigger, text):
    backup_daily(db)
    con = sqlite3.connect(db, timeout=10)
    cur = con.execute(
        f'UPDATE "{table}" SET "{resp_col}"=? WHERE "{key_col}"=?', (text, trigger)
    )
    if cur.rowcount != 1:
        con.rollback()
        con.close()
        sys.exit(
            f"Expected 1 row with {key_col}='{trigger}', got {cur.rowcount}. "
            "Create the Expect entry in JS8Spotter first. Nothing changed."
        )
    con.commit()
    con.close()


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--db")
    p.add_argument("--inspect", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--trigger", default="WX")
    p.add_argument("--grid", default="")
    p.add_argument("--table")
    p.add_argument("--key-col")
    p.add_argument("--resp-col")
    a = p.parse_args()

    if a.inspect:
        if not a.db:
            sys.exit("--inspect needs --db")
        inspect(a.db)
        return

    app = os.environ.get("AMBIENT_APP_KEY")
    key = os.environ.get("AMBIENT_API_KEY")
    if not (app and key):
        sys.exit("Set AMBIENT_APP_KEY and AMBIENT_API_KEY.")
    text = fmt(fetch(app, key, os.environ.get("AMBIENT_MAC")), a.grid)

    if a.dry_run:
        print(text)
        return
    if not all([a.db, a.table, a.key_col, a.resp_col]):
        sys.exit("Need --db --table --key-col --resp-col (run --inspect first).")
    update(a.db, a.table, a.key_col, a.resp_col, a.trigger, text)
    print(f"{a.trigger} -> {text}")


if __name__ == "__main__":
    main()
