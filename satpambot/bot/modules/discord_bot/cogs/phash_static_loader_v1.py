from __future__ import annotations

from discord.ext import commands

# -*- coding: utf-8 -*-
"""
Static pHash DB Loader (v1)
- Loads data/phash_static/*.json with key "phash"
- Exposes `bot.static_phash_db` (set[str])
- Optionally calls `satpambot.ml.guard_hooks.register_static_phash()` if available.
- No config/env changes required.
"""

import json
import logging
from pathlib import Path
from typing import Iterable, Set

log = logging.getLogger(__name__)

def _find_db_files() -> Iterable[Path]:
    roots = [
        Path.cwd() / "data" / "phash_static",
        Path(__file__).resolve().parents[6] / "data" / "phash_static",
    ]
    for r in roots:
        if r.exists():
            for p in sorted(r.glob("*.json")):
                yield p

def _load_phashes() -> Set[str]:
    out: Set[str] = set()
    for f in _find_db_files():
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            for h in data.get("phash", []):
                if isinstance(h, str) and len(h) >= 8:
                    out.add(h.lower())
        except Exception as e:
            log.exception("[static-phash-db] Failed reading %s: %s", f, e)
    return out

class StaticPhashDB(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def cog_load(self) -> None:
        phashes = _load_phashes()
        setattr(self.bot, "static_phash_db", phashes)
        log.info("[static-phash-db] loaded %d entries", len(phashes))

        # Best-effort hook into guard_hooks if present
        try:
            from satpambot.ml import guard_hooks as gh  # type: ignore

            for h in phashes:
                try:
                    # If the project exposes a registration function, use it.
                    fn = getattr(gh, "register_static_phash", None)
                    if callable(fn):
                        fn(h, tag="db_v1")
                except Exception:
                    pass
        except Exception:
            # Optional feature only
            pass
async def setup(bot: commands.Bot) -> None:  # discord.py 2.x style
    await bot.add_cog(StaticPhashDB(bot))