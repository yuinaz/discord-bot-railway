from __future__ import annotations
import os, logging, asyncio, time
import discord
from discord.ext import commands

log = logging.getLogger(__name__)

def _env_int(k: str, d: int) -> int:
    try: return int(os.getenv(k, str(d)))
    except Exception: return d

def _qna_channel_id() -> int:
    for k in ("LEARNING_QNA_CHANNEL_ID","QNA_ISOLATION_CHANNEL_ID","QNA_CHANNEL_ID"):
        v = os.getenv(k)
        if v and str(v).isdigit():
            return int(v)
    return 0

MARKER = "🤖 (auto-learn ping)"
TTL_SEC = _env_int("QNA_PING_TTL_SEC", 3600)
CLEAN_LIMIT = _env_int("QNA_PING_CLEAN_LIMIT", 50)

class QnaPingDedupeOverlay(commands.Cog):
    """Keep only one '(auto-learn ping)' message; delete older duplicates and expire by TTL."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.chan_id = _qna_channel_id()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        try:
            if not self.chan_id or message.author.id != self.bot.user.id:
                return
            if message.channel.id != self.chan_id:
                return
            if not isinstance(message.content, str) or MARKER not in message.content:
                return
            # Clean older pings
            ch = message.channel
            kept = False
            deleted = 0
            async for m in ch.history(limit=CLEAN_LIMIT):
                if m.id == message.id:
                    kept = True
                    continue
                if m.author.id == self.bot.user.id and MARKER in (m.content or ""):
                    try:
                        await m.delete()
                        deleted += 1
                    except Exception:
                        pass
            # Expire latest ping after TTL to avoid clutter
            await asyncio.sleep(min(3600, max(60, TTL_SEC)))
            try:
                # If the message still exists, delete it to keep channel clean
                m2 = await ch.fetch_message(message.id)
                await m2.delete()
            except Exception:
                pass
            if deleted:
                log.info("[qna-ping] cleaned %s older pings", deleted)
        except Exception as e:
            log.debug("[qna-ping] dedupe failed: %r", e)

async def setup(bot: commands.Bot):
    await bot.add_cog(QnaPingDedupeOverlay(bot))
