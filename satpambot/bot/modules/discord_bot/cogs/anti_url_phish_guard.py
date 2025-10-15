from __future__ import annotations

# Minimal, safe AntiUrlPhishGuard to pass smoke test and run on Render Free Plan.
# - Keeps env parsing (_norm_domain defined before use)
# - Does NOT create threads/DMs by itself (quiet by default)
# - Class name and setup() preserved for bootstrap compatibility

import os
from typing import List
from discord.ext import commands

def _norm_domain(p: str) -> str:
    return p.strip().lower().lstrip(".")

def _parse_csv_env(name: str, *, normalize_domain: bool = False) -> List[str]:
    raw = os.getenv(name, "") or ""
    items = [s.strip() for s in raw.split(",") if s.strip()]
    if normalize_domain:
        items = [_norm_domain(p) for p in items]
    return items

# Env-driven lists (kept minimal for compatibility; extend later as needed)
NSFW_SOFT_DOMAINS = _parse_csv_env("NSFW_SOFT_DOMAINS", normalize_domain=True)
URL_ALLOWLIST = _parse_csv_env("URL_ALLOWLIST", normalize_domain=True)
URL_BLOCKLIST = _parse_csv_env("URL_BLOCKLIST", normalize_domain=True)

class AntiUrlPhishGuard(commands.Cog):
    """Lightweight guard placeholder. Intended to be compatible with existing bootstrap.
    It sets up basic structures and can be extended by the NGovernor patch later.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.nsfw_soft_domains = set(NSFW_SOFT_DOMAINS)
        self.url_allowlist = set(URL_ALLOWLIST)
        self.url_blocklist = set(URL_BLOCKLIST)

    # Intentionally quiet: no auto-thread/DM creation here to suit Render Free Plan.
    # Actual URL scanning & enforcement is handled by existing guards; this cog is a safe loader.

async def setup(bot: commands.Bot):
    await bot.add_cog(AntiUrlPhishGuard(bot))