#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Auto-clean helper:
- Restores scripts/smoketest_all.py to the version bundled in this ZIP.
- Removes router&reseed add-ons if they exist:
  - scripts/smoke_router_reseed.py
  - scripts/apply_patch_smoke_router_reseed.py
- Also strips a previously injected block marked with
  "# --- injected by patch: router&reseed ---" if present.
"""
from __future__ import annotations

import sys, shutil
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TARGET = REPO / "scripts" / "smoketest_all.py"
PAYLOAD = Path(__file__).resolve().parent / "smoketest_all.py"

def strip_injected_block(text: str) -> str:
    marker = "# --- injected by patch: router&reseed ---"
    if marker not in text:
        return text
    # Remove from marker to EOF
    head = text.split(marker)[0].rstrip()
    return head + "\n"

def main() -> int:
    # 1) Replace smoketest_all.py with our known-good version
    if not PAYLOAD.exists():
        print("ERROR: bundled smoketest_all.py not found")
        return 2
    good = PAYLOAD.read_text(encoding="utf-8", errors="ignore")
    if TARGET.exists():
        # also attempt to strip injected area as extra safety
        cur = TARGET.read_text(encoding="utf-8", errors="ignore")
        if "# --- injected by patch: router&reseed ---" in cur:
            cur2 = strip_injected_block(cur)
            TARGET.write_text(cur2, encoding="utf-8")
    TARGET.write_text(good, encoding="utf-8")
    print("OK  : restored scripts/smoketest_all.py")

    # 2) Remove add-on scripts if exist
    addon1 = REPO / "scripts" / "smoke_router_reseed.py"
    addon2 = REPO / "scripts" / "apply_patch_smoke_router_reseed.py"
    for p in (addon1, addon2):
        if p.exists():
            try:
                p.unlink()
                print(f"OK  : removed {p.relative_to(REPO)}")
            except Exception as e:
                print(f"WARN: could not remove {p}: {e}")

    print("DONE: smoketest restored to original behavior.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
