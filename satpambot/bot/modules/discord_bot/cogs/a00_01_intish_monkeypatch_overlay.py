# a00_01_intish_monkeypatch_overlay.py
from __future__ import annotations
import sys, types, json, logging
from discord.ext import commands

log = logging.getLogger(__name__)

def intish(x, default=0):
    try:
        return int(x)
    except Exception:
        s = str(x).strip()
        if s.startswith("{") and s.endswith("}"):
            try:
                obj = json.loads(s)
                for k in ("senior_total_xp","value","v"):
                    if k in obj:
                        return int(obj[k])
            except Exception:
                pass
        digits = "".join(ch for ch in s if ch.isdigit())
        return int(digits or default)

TARGETS = (
    "satpambot.bot.modules.discord_bot.cogs.a08_xp_state_bootstrap_overlay",
    "satpambot.bot.modules.discord_bot.cogs.a08_passive_total_offset_overlay",
)

def _patch_module_int(modname: str) -> bool:
    mod = sys.modules.get(modname)
    if not isinstance(mod, types.ModuleType):
        return False
    try:
        setattr(mod, "int", intish)
        log.info("[intish] patched int() in %s", modname)
        return True
    except Exception as e:
        log.debug("[intish] patch failed in %s: %r", modname, e)
        return False

class IntishOverlay(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        ok = False
        for m in TARGETS:
            if _patch_module_int(m):
                ok = True
        if ok:
            log.info("[intish] int() patched for a08* modules to avoid JSON int crash")

async def setup(bot: commands.Bot):
    await bot.add_cog(IntishOverlay(bot))
