
import discord
from discord.ext import commands
from satpambot.bot.modules.discord_bot.helpers import banlog_thread

class BanLogRoute(commands.Cog):
    """Mirror ban events into a dedicated 'Ban Log' thread inside the log channel.
    This cog does not change existing logging; it only adds a dedicated thread entry.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        try:
            thread = await banlog_thread.ensure_ban_thread(guild)
            if not thread:
                return
            emb = discord.Embed(
                title="🚫 User banned",
                description=f"{user.mention} (`{user.id}`)",
                colour=discord.Colour.red(),
            )
            emb.set_footer(text="SatpamBot • Ban log")
            await thread.send(embed=emb, allowed_mentions=discord.AllowedMentions.none())
        except Exception:
            pass

async def setup(bot: commands.Bot):
    await bot.add_cog(BanLogRoute(bot))

def legacy_setup(bot: commands.Bot):
    bot.add_cog(BanLogRoute(bot))
