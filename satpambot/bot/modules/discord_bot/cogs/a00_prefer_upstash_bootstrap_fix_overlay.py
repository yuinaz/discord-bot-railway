
# a00_prefer_upstash_bootstrap_fix_overlay.py (v7.1)
import json, logging, asyncio
from discord.ext import commands
log = logging.getLogger(__name__)
async def _safe_parse_int(val, default=0):
    try:
        if isinstance(val, (int, float)): return int(val)
        if isinstance(val, str):
            s = val.strip()
            if s.startswith("{") and s.endswith("}"):
                try:
                    obj = json.loads(s)
                    for k in ("senior_total_xp","total","value"):
                        if k in obj: return int(obj[k])
                except Exception:
                    pass
            return int(s)
    except Exception:
        return int(default)
    return int(default)
class PreferUpstashBootstrapFix(commands.Cog):
    def __init__(self, bot): self.bot=bot
    @commands.Cog.listener()
    async def on_ready(self):
        # Try to patch target module function if present
        try:
            import satpambot.bot.modules.discord_bot.cogs.a00_prefer_upstash_bootstrap as m
            if hasattr(m, "_fetch_state_from_upstash"):
                orig = m._fetch_state_from_upstash
                async def wrapper():
                    try:
                        state = await orig()
                        # normalize fields if any is json-string
                        if isinstance(state, dict):
                            for k,v in list(state.items()):
                                state[k] = await _safe_parse_int(v, 0)
                        return state
                    except Exception as e:
                        log.info("[upstash-fix] bootstrap fetch failed: %r", e)
                        return {"senior_total":0,"junior_total":0}
                m._fetch_state_from_upstash = wrapper
                log.info("[upstash-fix] function _fetch_state_from_upstash patched")
        except Exception as e:
            log.info("[upstash-fix] patch module missing: %r", e)
async def setup(bot):
    try: await bot.add_cog(PreferUpstashBootstrapFix(bot))
    except Exception as e: log.info("[upstash-fix] setup swallowed: %r", e)
