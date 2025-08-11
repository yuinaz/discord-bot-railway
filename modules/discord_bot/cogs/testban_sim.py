from discord.ext import commands
import discord
from datetime import datetime, timezone
from pathlib import Path

class TestbanSim(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="testban", aliases=["tb"])
    async def testban(self, ctx: commands.Context, *, reason: str="Simulasi ban"):
        member = ctx.author
        embed = discord.Embed(
            title="Simulasi Ban oleh SatpamBot",
            description=f"{member.mention} terdeteksi mengirim pesan mencurigakan.\n*(Simulasi)*",
            color=discord.Color.orange(),
            timestamp=datetime.now(timezone.utc),
        )
        # Thumbnail avatar
        try:
            if member.display_avatar:
                embed.set_thumbnail(url=member.display_avatar.url)
        except Exception:
            pass

        # Coba lampirkan sticker FibiLaugh dari assets (jika ada)
        file = None
        try:
            base = Path(__file__).resolve().parents[2]  # .../modules
            img = base / "assets" / "FibiLaugh.png"
            if img.exists():
                file = discord.File(str(img), filename="fibilaugh.png")
                embed.set_image(url="attachment://fibilaugh.png")
        except Exception:
            file = None

        if file:
            await ctx.send(embed=embed, file=file)
        else:
            await ctx.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(TestbanSim(bot))
