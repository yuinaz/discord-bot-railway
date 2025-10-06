
"""
scripts/force_checkpoint.py
---------------------------------
Trigger a one-off checkpoint without bot commands.
- It sets a DB meta flag "force_checkpoint" = current timestamp.
- The DiscordStateCheckpoint cog (already running in the bot) will notice and post
  a fresh pinned attachment within ~90s (anti-spam protected).

Usage:
  python scripts/force_checkpoint.py
"""
import os, sqlite3, time, sys

def _db_path() -> str:
    return os.getenv("NEUROLITE_MEMORY_DB",
        os.path.join(os.path.dirname(__file__), "..","satpambot","data","memory.sqlite3"))

def _open_db():
    path = _db_path()
    d = os.path.dirname(path)
    if d and not os.path.exists(d):
        try: os.makedirs(d, exist_ok=True)
        except Exception: pass
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    return con

def _ensure_meta(con: sqlite3.Connection):
    con.execute("""CREATE TABLE IF NOT EXISTS learning_progress_meta(
        key TEXT PRIMARY KEY,
        value TEXT
    )""")
    con.commit()

def main():
    con = _open_db()
    with con:
        _ensure_meta(con)
        now_ts = int(time.time())
        con.execute("INSERT INTO learning_progress_meta(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                    ("force_checkpoint", str(now_ts)))
    print(f"[OK] force_checkpoint flag set at ts={now_ts}. The bot will pin a fresh state in ~90s.")

if __name__ == "__main__":
    main()
