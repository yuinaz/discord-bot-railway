from __future__ import annotations

import discord
from discord.ext import commands

from satpambot.bot.modules.discord_bot.helpers import banlog_thread


class BanLogRoute(commands.Cog):







    """Route ban events into a dedicated 'Ban Log' thread in the log channel.







    This does NOT change other logging







    it only adds a thread entry for bans.







    """















    def __init__(self, bot: commands.Bot):







        self.bot = bot















    @commands.Cog.listener()







    async def on_member_ban(self, guild: discord.Guild, user: discord.User):







        try:







            th = await banlog_thread.ensure_ban_thread(guild)







            if not th:







                return







            emb = discord.Embed(







                title="🚫 User banned",







                description=f"{user.mention} (`{user.id}`)",







                colour=discord.Colour.red(),







            )







            emb.set_footer(text="SatpamBot • Ban log")







            await th.send(embed=emb, allowed_mentions=discord.AllowedMentions.none())







        except Exception:







            pass























async def setup(bot: commands.Bot):







    await bot.add_cog(BanLogRoute(bot))







