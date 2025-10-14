
# -*- coding: utf-8 -*-
"""
Overlay: a02_miner_accel_overlay_safe
- Provides sanitized numeric factors for miner accel to avoid ValueError on malformed ENV like '0.85,'.
- If the real overlay exists and works, this overlay becomes a no-op.
"""
import os
import re

def _clean_num(val: str, default: float) -> float:
    if val is None:
        return default
    # Keep digits, dot, minus; strip trailing commas/semicolons/spaces
    cleaned = re.sub(r"[^0-9eE+\-\.]+", "", val.strip())
    try:
        return float(cleaned)
    except Exception:
        return default

# Export sane defaults as ENV so downstream overlays read them safely.
# These names are generic; if unused, harmless.
os.environ.setdefault("SATPAMBOT_MINER_ACCEL_TEXT", "0.93")
os.environ.setdefault("SATPAMBOT_MINER_ACCEL_PHISH", "1.01")
os.environ.setdefault("SATPAMBOT_MINER_ACCEL_SLANG", "1.05")

# Clean in-place in case they already exist but malformed
os.environ["SATPAMBOT_MINER_ACCEL_TEXT"]  = str(_clean_num(os.getenv("SATPAMBOT_MINER_ACCEL_TEXT"), 0.93))
os.environ["SATPAMBOT_MINER_ACCEL_PHISH"] = str(_clean_num(os.getenv("SATPAMBOT_MINER_ACCEL_PHISH"), 1.01))
os.environ["SATPAMBOT_MINER_ACCEL_SLANG"] = str(_clean_num(os.getenv("SATPAMBOT_MINER_ACCEL_SLANG"), 1.05))

async def setup(bot):
    # No cog to add; this overlay just sanitizes ENV values early.
    return
