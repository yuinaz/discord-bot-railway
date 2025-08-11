from discord.ext import commands
import discord

class PrefixGuard(commands.Cog):
    """Failsafe: ensure prefix commands are processed even if other on_message handlers skip it."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message or message.author.bot:
            return
        try:
            await self.bot.process_commands(message)
        except Exception:
            pass

    @commands.command(name="ping")
    async def ping(self, ctx: commands.Context):
        await ctx.send("pong")

async def setup(bot: commands.Bot):
    await bot.add_cog(PrefixGuard(bot))
