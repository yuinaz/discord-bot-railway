import os
import discord
from discord.ext import commands

LOG_CHANNEL_NAME = os.getenv("LOG_CHANNEL_NAME", "log-botphising")

class BotOnlineAnnounce(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._announced = False

    @commands.Cog.listener()
    async def on_ready(self):
        if self._announced:
            return
        self._announced = True
        for guild in self.bot.guilds:
            ch = discord.utils.get(guild.text_channels, name=LOG_CHANNEL_NAME)
            if ch and ch.permissions_for(guild.me).send_messages:
                try:
                    await ch.send("✅ SatpamBot online dan siap berjaga.")
                except Exception:
                    pass

    # Command diagnosa untuk cek extension yang aktif
    @commands.command(name="sbwho")
    async def sbwho(self, ctx: commands.Context):
        try:
            exts = sorted(self.bot.extensions.keys())
            await ctx.send("Loaded extensions: " + ", ".join(exts))
        except Exception as e:
            await ctx.send(f"diag err: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(BotOnlineAnnounce(bot))
