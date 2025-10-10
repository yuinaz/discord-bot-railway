
import os
import logging
import discord
from discord.ext import commands

log = logging.getLogger(__name__)

def _int(x, d=0):
    try: return int(x)
    except Exception: return d

class ShadowPublicSilencer(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.allowed_ids = set([_int(os.getenv("LOG_CHANNEL_ID", "0"))])
        self.log_blocked = os.getenv("SILENCER_LOG_BLOCKED", "0") == "1"
        self._patch()

    def _patch(self):
        orig = discord.abc.Messageable.send

        async def _send(self, *args, **kwargs):
            # allow list only
            cid = getattr(self, "id", None)
            pid = getattr(getattr(self, "parent", None), "id", None)
            if cid in self.allowed_ids or pid in self.allowed_ids:
                return await orig(self, *args, **kwargs)
            # block silently or log only once
            if self.bot and getattr(self.bot, "user", None) and self.bot.user:
                pass
            if self.log_blocked:
                log.info("[shadow_silencer] blocked send to #%s (guild=%s)", getattr(self, "name", "?"), getattr(getattr(self, "guild", None), "name", "?"))
            # swallow
            return None

        discord.abc.Messageable.send = _send
        log.info("[shadow_silencer] whitelist ids set: %s", list(self.allowed_ids))
        log.info("[shadow_silencer] active (public allowed? False)")

async def setup(bot: commands.Bot):
    await bot.add_cog(ShadowPublicSilencer(bot))
