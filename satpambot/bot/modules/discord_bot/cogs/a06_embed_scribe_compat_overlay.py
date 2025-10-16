
import logging
from discord.ext import commands

log = logging.getLogger(__name__)

class _EmbedScribeCompat(commands.Cog):
    """Adds a minimal 'upsert' to EmbedScribe if absent.
    This mirrors the common pattern: if message_id provided -> edit; else -> send.
    """
    def __init__(self, bot):
        self.bot = bot
        try:
            from satpambot.bot.utils.embed_scribe import EmbedScribe  # type: ignore
        except Exception as e:
            log.warning("[scribe_compat] embed_scribe not available: %r", e)
            self.EmbedScribe = None
            return

        self.EmbedScribe = EmbedScribe
        if not hasattr(EmbedScribe, "upsert"):
            log.info("[scribe_compat] injecting EmbedScribe.upsert")
            async def upsert(self_es, channel, *, content=None, embed=None, message_id=None, **kwargs):
                try:
                    if message_id:
                        try:
                            msg = await channel.fetch_message(int(message_id))
                            return await msg.edit(content=content, embed=embed, **kwargs)
                        except Exception:
                            # fall back to send
                            return await channel.send(content=content, embed=embed, **kwargs)
                    else:
                        return await channel.send(content=content, embed=embed, **kwargs)
                except Exception as e:
                    log.warning("[scribe_compat] upsert failed: %r", e)
                    raise
            setattr(EmbedScribe, "upsert", upsert)

async def setup(bot):
    await bot.add_cog(_EmbedScribeCompat(bot))

def setup_legacy(bot):
    bot.add_cog(_EmbedScribeCompat(bot))
