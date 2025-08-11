from discord.ext import commands
import discord
from datetime import datetime, timezone

class TestbanSim(commands.Cog):
    def __init__(self, bot: commands.Bot): self.bot = bot

    @commands.command(name="testban", aliases=["tb"])
    async def testban(self, ctx: commands.Context, *, reason: str="Simulasi ban"):
        member = ctx.author
        embed = discord.Embed(
            title="Simulasi Ban oleh SatpamBot",
            description=f"{member.mention} terdeteksi mengirim pesan mencurigakan.\n*(Simulasi)*",
            color=discord.Color.orange(),
            timestamp=datetime.now(timezone.utc),
        )
        try:
            if member.display_avatar: embed.set_thumbnail(url=member.display_avatar.url)
        except Exception: pass
        await ctx.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(TestbanSim(bot))
