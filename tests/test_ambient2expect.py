import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import os
import sqlite3
import tempfile
from datetime import datetime

from ambient2expect import KEEP_BACKUPS, backup_daily, fmt, mark_stale

assert "CALM" in fmt({"windspeedmph": 0, "windgustmph": 0})
assert fmt({"windspeedmph": 0, "windgustmph": 15, "winddir": 315}) == "WX NW0G15"
assert fmt({"dailyrainin": 0.03, "eventrainin": 0.2}) == "WX R0.03 EVT0.20"
assert fmt({"eventrainin": 0}) == "WX"

with tempfile.TemporaryDirectory() as d:
    db = os.path.join(d, "js8spotter.db")
    sqlite3.connect(db).close()
    for day in range(1, 10):
        open(f"{db}.bak-202601{day:02d}", "w").close()
    open(f"{db}.blank", "w").close()  # not a backup, must survive

    backup_daily(db)

    left = sorted(f for f in os.listdir(d) if ".bak-" in f)
    assert len(left) == KEEP_BACKUPS, left
    assert left[-1] == f"js8spotter.db.bak-{datetime.now():%Y%m%d}", left
    assert "js8spotter.db.bak-20260101" not in left, left
    assert os.path.exists(f"{db}.blank")

    con = sqlite3.connect(db)
    con.execute("CREATE TABLE expect (expect, reply)")
    con.execute("INSERT INTO expect VALUES ('WX', 'WX 1619L 48F'), ('COND', 'G')")
    con.commit()
    mark_stale(db, "expect", "expect", "reply", "WX")
    mark_stale(db, "expect", "expect", "reply", "WX")  # only once
    rows = dict(con.execute("SELECT * FROM expect"))
    assert rows == {"WX": "WX 1619L 48F STALE", "COND": "G"}, rows
    con.close()
print("ok")
