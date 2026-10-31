import os
import sqlite3
import tempfile
from datetime import datetime

from ambient2expect import KEEP_BACKUPS, backup_daily

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
print("ok")
