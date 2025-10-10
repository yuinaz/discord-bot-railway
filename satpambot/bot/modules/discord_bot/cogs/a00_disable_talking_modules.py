from discord.ext import commands
import logging
log = logging.getLogger(__name__)
BLOCK_PREFIXES = [
    "satpambot.bot.modules.discord_bot.cogs.chat_neurolite",
    "satpambot.bot.modules.discord_bot.cogs.public_send_router",
    "satpambot.bot.modules.discord_bot.cogs.slash_list_broadcast",
    "satpambot.bot.modules.discord_bot.cogs.diag_public",
]
def _is_blocked(name: str) -> bool:
    for p in BLOCK_PREFIXES:
        if name.startswith(p): return True
    return False
class DisableTalking(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        removed = []
        for name in list(bot.extensions.keys()):
            if _is_blocked(name):
                try:
                    bot.unload_extension(name); removed.append(name)
                except Exception: pass
        if removed: log.info("[disable-talking] unloaded: %s", removed)
        self._orig_load_ext = bot.load_extension
        def _guarded_load_ext(name, *a, **kw):
            if _is_blocked(name):
                log.info("[disable-talking] suppress load: %s", name); return
            return self._orig_load_ext(name, *a, **kw)
        bot.load_extension = _guarded_load_ext
        log.info("[disable-talking] active; blocked prefixes=%s", BLOCK_PREFIXES)
    def cog_unload(self):
        try: self.bot.load_extension = self._orig_load_ext
        except Exception: pass
async def setup(bot: commands.Bot):
    await bot.add_cog(DisableTalking(bot))
