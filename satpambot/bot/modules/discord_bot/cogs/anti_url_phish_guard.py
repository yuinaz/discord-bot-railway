from __future__ import annotations

import logging
import os
from typing import Iterable, Set
from discord.ext import commands

log = logging.getLogger(__name__)


def _norm_domain(d: str) -> str:
    d = (d or "").strip().lower()
    # strip scheme and path if given
    if d.startswith("http://") or d.startswith("https://"):
        try:
            from urllib.parse import urlparse
            d = urlparse(d).hostname or d
        except Exception:
            pass
    return d.lstrip(".")


def _parse_csv_env(key: str, *, normalize_domain: bool = False) -> Set[str]:
    raw = os.getenv(key, "") or ""
    out: Set[str] = set()
    for part in (p.strip() for p in raw.split(",") if p.strip()):
        out.add(_norm_domain(part) if normalize_domain else part)
    return out


class AntiUrlPhishGuard(commands.Cog):
    """Lightweight placeholder for anti-url guard (TKSD-stable hotfix).
    - Keeps import/setup stable for smoke tests and runtime.
    - Reads optional envs for future use but performs no message filtering here.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.enabled = (os.getenv("ANTI_URL_GUARD_ENABLE", "0").lower() not in {"0", "false", "no"})
        self.block_domains = _parse_csv_env("BLOCK_DOMAINS", normalize_domain=True)
        self.allow_domains = _parse_csv_env("ALLOW_DOMAINS", normalize_domain=True)
        log.info(
            "[anti_url_phish_guard] ready (enabled=%s, block=%d, allow=%d)",
            self.enabled, len(self.block_domains), len(self.allow_domains)
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(AntiUrlPhishGuard(bot))
