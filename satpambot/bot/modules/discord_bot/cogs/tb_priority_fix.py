
import asyncio
import logging
from discord.ext import commands

log = logging.getLogger(__name__)

PREFERRED_COG_NAME = "TBShimFormatted"  # class name in tb_shim.py
LOWER_PRIORITY_MODULE_SUFFIXES = (".ban_secure", ".tb_alias")  # any tb from these will be demoted/removed

def _origin_module(cmd) -> str:
    return getattr(getattr(cmd, "callback", None), "__module__", "") or ""

class TBPriorityFix(commands.Cog):
    """Ensure the active prefix command `tb` comes from tb_shim only.

    This cog does NOT change any config. It waits until commands are registered,
    then if `tb` is owned by lower‑priority cogs (ban_secure/tb_alias), it removes
    them and re‑registers `tb` from `tb_shim`.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # schedule stabilization in the running loop (works in smoke + real bot)
        try:
            self._task = asyncio.create_task(self._stabilize())
        except RuntimeError:
            # no running loop (rare in exotic loaders) — fall back
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._task = loop.create_task(self._stabilize())

    def cog_unload(self) -> None:
        t = getattr(self, "_task", None)
        if t:
            t.cancel()

    async def _stabilize(self) -> None:
        # try for ~10s while cogs register
        for _ in range(100):
            if await self._ensure_preferred_tb():
                return
            await asyncio.sleep(0.1)
        # last attempt
        await self._ensure_preferred_tb()

    async def _ensure_preferred_tb(self) -> bool:
        # If no tb yet, try again later
        active_tb = self.bot.get_command("tb")
        if active_tb is None:
            return False

        active_origin = _origin_module(active_tb)
        # if already preferred, just prune shadow copies (if any)
        if active_origin.endswith(".tb_shim"):
            pruned = 0
            # remove any other 'tb' definitions from lower-priority cogs
            for cog in list(self.bot.cogs.values()):
                for cmd in list(getattr(cog, "get_commands", lambda: [])()):
                    if cmd.name != "tb" or cmd is active_tb:
                        continue
                    other_origin = _origin_module(cmd)
                    if other_origin.endswith(LOWER_PRIORITY_MODULE_SUFFIXES):
                        try:
                            self.bot.remove_command("tb")
                            pruned += 1
                        except Exception:
                            pass
            if pruned:
                log.info("[tb_priority_fix] removed %d duplicate tb from lower-priority cogs", pruned)
            return True

        # Not preferred — see if tb_shim is loaded so we can swap
        shim = self.bot.get_cog(PREFERRED_COG_NAME)
        if shim:
            shim_tb = None
            for cmd in shim.get_commands():
                if cmd.name == "tb":
                    shim_tb = cmd
                    break
            if shim_tb:
                # remove current mapping and re-add preferred from shim
                try:
                    self.bot.remove_command("tb")
                except Exception:
                    pass
                try:
                    self.bot.add_command(shim_tb)
                    log.info("[tb_priority_fix] switched tb to tb_shim (from %s)", active_origin)
                    return True
                except Exception as e:
                    log.warning("[tb_priority_fix] failed to register tb from shim: %s", e)
                    return False

        # shim not ready yet
        return False

async def setup(bot: commands.Bot):
    await bot.add_cog(TBPriorityFix(bot))
