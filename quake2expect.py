#!/usr/bin/env python3
"""
quake2expect.py - put recent earthquakes near your grid square into a
JS8Spotter Expect response, so `YOURCALL E? QUAKE` returns them.

Stdlib only, no keys needed (USGS feed is public). Usage:
  Preview:
    python3 quake2expect.py --grid DN43AP --dry-run
  Run for real (cron every 15 min):
    python3 quake2expect.py --grid DN43AP --db /path/js8spotter.db \
        --table expect --key-col expect --resp-col reply
"""
import argparse
import json
import math
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

from ambient2expect import cardinal, update

API = "https://earthquake.usgs.gov/fdsnws/event/1/query"
KM_PER_MI = 1.609344
EARTH_MI = 3958.8


def grid2latlon(grid):
    """Center of a 4- or 6-char Maidenhead grid square."""
    g = grid.upper()
    lon = (ord(g[0]) - 65) * 20 - 180 + int(g[2]) * 2
    lat = (ord(g[1]) - 65) * 10 - 90 + int(g[3])
    if len(g) >= 6:
        lon += (ord(g[4]) - 65) / 12 + 1 / 24
        lat += (ord(g[5]) - 65) / 24 + 1 / 48
    else:
        lon += 1
        lat += 0.5
    return lat, lon


def dist_bearing(lat1, lon1, lat2, lon2):
    """Miles and degrees from point 1 to point 2."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    mi = 2 * EARTH_MI * math.asin(math.sqrt(a))
    brg = math.degrees(math.atan2(
        math.sin(dl) * math.cos(p2),
        math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl),
    ))
    return mi, brg % 360


def fetch(lat, lon, radius_mi, hours, min_mag):
    start = datetime.now(timezone.utc) - timedelta(hours=hours)
    q = urllib.parse.urlencode({
        "format": "geojson",
        "latitude": f"{lat:.4f}",
        "longitude": f"{lon:.4f}",
        "maxradiuskm": f"{radius_mi * KM_PER_MI:.1f}",
        "starttime": start.strftime("%Y-%m-%dT%H:%M:%S"),
        "minmagnitude": min_mag,
        "orderby": "magnitude",
    })
    req = urllib.request.Request(f"{API}?{q}", headers={"User-Agent": "quake2expect"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.load(r)["features"]


def fmt(quakes, lat, lon, hours, min_mag, radius_mi):
    """Run time, then largest quake in the window plus a count. JS8-safe.
    The run time shows callers how old the reply is if the feed goes down.
    e.g. 'QUAKE 1415L 24H 3 MAX M3.1 28MI NE 0412L'"""
    head = f"QUAKE {datetime.now():%H%M}L {hours}H"
    if not quakes:
        return f"{head} NONE M{min_mag:g}+ {radius_mi}MI"
    q = quakes[0]  # orderby=magnitude, so largest first
    qlon, qlat = q["geometry"]["coordinates"][:2]
    mi, brg = dist_bearing(lat, lon, qlat, qlon)
    t = datetime.fromtimestamp(q["properties"]["time"] / 1000, tz=timezone.utc)
    return (f"{head} {len(quakes)} MAX M{q['properties']['mag']:.1f} "
            f"{round(mi)}MI {cardinal(brg)} {t.astimezone():%H%M}L")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--grid", required=True)
    p.add_argument("--radius", type=int, default=100, help="miles")
    p.add_argument("--hours", type=int, default=24)
    p.add_argument("--min-mag", type=float, default=2.5)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--trigger", default="QUAKE")
    p.add_argument("--db")
    p.add_argument("--table")
    p.add_argument("--key-col")
    p.add_argument("--resp-col")
    a = p.parse_args()

    lat, lon = grid2latlon(a.grid)
    text = fmt(fetch(lat, lon, a.radius, a.hours, a.min_mag),
               lat, lon, a.hours, a.min_mag, a.radius)

    if a.dry_run:
        print(text)
        return
    if not all([a.db, a.table, a.key_col, a.resp_col]):
        sys.exit("Need --db --table --key-col --resp-col.")
    update(a.db, a.table, a.key_col, a.resp_col, a.trigger, text)
    print(f"{a.trigger} -> {text}")


if __name__ == "__main__":
    main()
