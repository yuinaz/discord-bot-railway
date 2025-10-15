#!/usr/bin/env python3
"""
Promote phase to 'senior' immediately if TK XP >= TK_REQUIRED_XP (default 1500).
Works with Upstash if configured; always writes local fallback phase.json too.
Usage:
  python -m scripts.promote_phase_if_ready
  # or customize threshold:
  TK_REQUIRED_XP=1500 python -m scripts.promote_phase_if_ready
"""
import os
from satpambot.bot.modules.discord_bot.helpers.phase_utils import get_tk_total, set_phase, get_phase

def main():
    need = int(os.getenv("TK_REQUIRED_XP", "1500"))
    cur = int(get_tk_total())
    print(f"[promote] current TK XP = {cur}, required = {need}")
    if cur >= need:
        set_phase("senior")
        print("[promote] phase set to 'senior'")
    else:
        print("[promote] not enough TK XP; skipped")
    print("[promote] phase now =", get_phase())

if __name__ == "__main__":
    main()