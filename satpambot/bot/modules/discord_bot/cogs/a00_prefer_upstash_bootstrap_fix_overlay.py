
from discord.ext import commands
"""
a00_prefer_upstash_bootstrap_fix_overlay.py
- Monkeypatch parser in prefer_upstash_bootstrap to handle JSON-like values gracefully.
"""
import json, logging

log = logging.getLogger(__name__)

def _parse_intish(v):
    if v is None: return 0
    if isinstance(v, (int, float)): return int(v)
    s = str(v).strip()
    if not s: return 0
    # Try pure int
    try: return int(s)
    except Exception: pass
    # Try json
    try:
        j = json.loads(s)
        # accept {"senior_total_xp": 2691} or numbers
        if isinstance(j, dict):
            for k in ("senior_total_xp","total","value","v"):
                if k in j:
                    try: return int(j[k])
                    except Exception: continue
            # fallback: first int in dict
            for vv in j.values():
                try: return int(vv)
                except Exception: continue
        elif isinstance(j, (int, float, str)):
            return int(j)
    except Exception: pass
    # Last resort: extract digits
    digits = "".join(ch for ch in s if ch.isdigit())
    return int(digits or 0)

class PreferUpstashBootstrapFix(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        try:
            import satpambot.bot.modules.discord_bot.cogs.a00_prefer_upstash_bootstrap as m
            if hasattr(m, "_fetch_state_from_upstash"):
                orig = m._fetch_state_from_upstash
                async def wrap():
                    raw = await orig()
                    try:
                        raw["senior_total"] = _parse_intish(raw.get("senior_total"))
                    except Exception: pass
                    return raw
                m._fetch_state_from_upstash = wrap
                log.info("[prefer-upstash-fix] patched _fetch_state_from_upstash")
        except Exception as e:
            log.debug("[prefer-upstash-fix] module not available: %r", e)
async def setup(bot):
    await bot.add_cog(PreferUpstashBootstrapFix(bot))

def setup(bot):
    try:
        import asyncio
        if asyncio.get_event_loop().is_running():
            return asyncio.create_task(bot.add_cog(PreferUpstashBootstrapFix(bot)))
    except Exception:
        pass
    return bot.add_cog(PreferUpstashBootstrapFix(bot))