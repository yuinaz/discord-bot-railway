\
from __future__ import annotations
import os, time, logging
try:
    import discord
    from discord.ext import commands
except Exception:
    class discord:  # type: ignore
        class Message: ...
    class commands:  # type: ignore
        class Cog:
            @staticmethod
            def listener(*a,**k):
                def _w(f): return f
                return _w
        @staticmethod
        def listener(*a,**k):
            def _w(f): return f
            return _w
try:
    from satpambot.bot.modules.discord_bot.helpers.upstash_client import UpstashClient
except Exception:
    UpstashClient=None
def _cfg(k,d=""):
    try:
        from satpambot.config.auto_defaults import cfg_str as _cs
        return _cs(k,d)
    except Exception:
        return os.getenv(k,d)
SENIOR_KEY=_cfg("XP_SENIOR_KEY","xp:bot:senior_total_v2")
SILENT_NO_SHIM=(_cfg("XP_SILENT_NO_SHIM","1") or "1").lower() in ("1","true","yes","on")
DELTA_DEFAULT=int((_cfg("XP_RENDER_DELTA_DEFAULT","0") or "0"))
WARN_THROTTLE_SEC=int((_cfg("XP_WARN_THROTTLE_SEC","3600") or "3600"))
log=logging.getLogger(__name__)
_client=None
try: _client=UpstashClient() if UpstashClient else None
except Exception: _client=None
_version="v2025-10-24-nos"
log.info("[xp-render] %s loaded (silent=%s, key=%s, client=%s)",_version,SILENT_NO_SHIM,SENIOR_KEY,bool(_client))
_last_warn=0.0
def _warn_once(msg:str):
    global _last_warn
    now=time.time()
    if now-_last_warn>=WARN_THROTTLE_SEC: _last_warn=now; log.warning("[xp-render] %s",msg)
    else: log.debug("[xp-render] %s (suppressed)",msg)
async def _award_internal(delta:int)->bool:
    if not delta: return True
    if _client and getattr(_client,"enabled",False):
        try:
            await _client.incrby(SENIOR_KEY,int(delta)); log.info("[xp-render] +%s -> %s (upstash)",delta,SENIOR_KEY); return True
        except Exception as e:
            if not SILENT_NO_SHIM: _warn_once(f"upstash incr fail: {e!r}"); return False
    if not SILENT_NO_SHIM: _warn_once("no client; skipping award")
    return False
async def award_xp(delta:int=None)->bool:
    return await _award_internal(int(delta if delta is not None else DELTA_DEFAULT))
class XpHistoryRenderOverlay(commands.Cog):
    def __init__(self,bot): self.bot=bot
    async def award_from_render(self,delta:int|None=None):
        await award_xp(delta if delta is not None else DELTA_DEFAULT)
async def setup(bot):
    await bot.add_cog(XpHistoryRenderOverlay(bot))
