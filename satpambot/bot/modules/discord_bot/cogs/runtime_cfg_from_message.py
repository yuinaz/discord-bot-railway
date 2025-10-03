import asyncio
import discord
from discord.ext import commands

class RuntimeCfgFromMessage(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _apply(self):
        # Panggil helper kalau ada; kalau tidak, no-op (aman)
        helper = (globals().get('_apply_config_from_message')
                  or globals().get('_apply'))
        if callable(helper):
            try:
                res = helper(self)
                if asyncio.iscoroutine(res):
                    await res
            except Exception:
                # Jangan ganggu event loop di prod
                pass

    @commands.Cog.listener()
    async def on_ready(self):
        await self._apply()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # THREAD/FORUM EXEMPTION — auto-inserted
        ch = getattr(message, "channel", None)
        if ch is not None:
            try:
                if isinstance(ch, getattr(discord, "Thread", tuple())):
                    return
                ctype = getattr(ch, "type", None)
                if ctype in {
                    getattr(discord.ChannelType, "public_thread", None),
                    getattr(discord.ChannelType, "private_thread", None),
                    getattr(discord.ChannelType, "news_thread", None),
                }:
                    return
            except Exception:
                pass
        await self._apply()

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        await self._apply()

async def setup(bot: commands.Bot):
    await bot.add_cog(RuntimeCfgFromMessage(bot))
