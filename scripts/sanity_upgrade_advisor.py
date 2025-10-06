
# scripts/sanity_upgrade_advisor.py
# Quick offline sanity: open DB and print proposed upgrades (no Discord required).
import os, sqlite3
from satpambot.bot.modules.discord_bot.helpers import upgrade_rules

def _db_path() -> str:
    return os.getenv("NEUROLITE_MEMORY_DB",
        os.path.join(os.path.dirname(__file__), "..","satpambot","data","memory.sqlite3"))

def main():
    con = sqlite3.connect(_db_path())
    con.row_factory = sqlite3.Row
    props = upgrade_rules.evaluate(con)
    print("Proposals:", [p["key"] for p in props])

if __name__ == "__main__":
    main()
