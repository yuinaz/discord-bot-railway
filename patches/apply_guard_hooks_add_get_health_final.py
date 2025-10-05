#!/usr/bin/env python3
# Append get_health() into satpambot/ml/guard_hooks.py if it's missing.
# Safe: no overwrites, no config changes, no ruff formatting.
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TARGET = REPO / "satpambot" / "ml" / "guard_hooks.py"

STUB = '''
# --- appended for watchdog health (safe, minimal) ---
def get_health():
    """Return a tiny health dict for watchdogs."""
    try:
        import time
        ts = int(time.time())
    except Exception:
        ts = 0
    return {"status": "ok", "ts": ts, "details": {"source": "guard_hooks:appended"}}
'''.lstrip()

def main():
    if not TARGET.exists():
        print(f"[ERROR] {TARGET} not found.")
        return 2
    src = TARGET.read_text(encoding="utf-8", errors="ignore")
    if "def get_health" in src:
        print("[OK] get_health() already present — no changes.")
        return 0
    with TARGET.open("a", encoding="utf-8", newline="\n") as f:
        if not src.endswith("\n"):
            f.write("\n")
        f.write(STUB)
    print("[OK] get_health() appended.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
