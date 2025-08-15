
from __future__ import annotations
import os
from ..helpers.sticky import upsert_sticky_embed
from ..helpers.sticky import upsert_sticky
import discord
from discord.ext import commands

import time
_PRESENCE_LAST_TS = {}
_PRESENCE_MIN_SEC = int(os.getenv('PRESENCE_COOLDOWN','300'))

class PresenceFix(commands.Cog):
    """Paksa presence ONLINE + activity default, dan sediakan !alive."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        try:
            g = getattr(getattr(ctx,'guild',None) or getattr(message,'guild',None) or getattr(self.bot,'guild',None), 'id', None)
        except Exception:
            g = None
        if g is not None:
            now = time.time()
            if (_PRESENCE_LAST_TS.get(g) and now - _PRESENCE_LAST_TS[g] < _PRESENCE_MIN_SEC):
                return
            _PRESENCE_LAST_TS[g] = now
        mode = os.getenv("BOT_PRESENCE", "online").lower()
        mapping = {
            "online": discord.Status.online,
            "idle": discord.Status.idle,
            "dnd": discord.Status.do_not_disturb,
            "invisible": discord.Status.invisible,
        }
        status = mapping.get(mode, discord.Status.online)
        try:
            await self.bot.change_presence(
                status=status,
                activity=discord.Game(name=os.getenv("BOT_ACTIVITY", "Satpam aktif"))
            )
        except Exception:
            pass
        # Optional: kirim info singkat ke log channel
        raw = os.getenv("LOG_CHANNEL_ID")
        if raw and raw.isdigit():
            ch = None
            for g in self.bot.guilds:
                c = g.get_channel(int(raw))
                if c: ch = c; break
            if ch:
                try:
                    await ch.send(f"✅ Online sebagai **{self.bot.user}** | presence={status.name}")
                except Exception:
                    pass

    @commands.command(name="alive")
    async def alive(self, ctx: commands.Context):
        await ctx.reply("✅ Bot online & siap jaga.", mention_author=False)

async def setup(bot: commands.Bot):
    await bot.add_cog(PresenceFix(bot))
