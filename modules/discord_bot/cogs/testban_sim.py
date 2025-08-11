from discord.ext import commands
import discord, os
from datetime import datetime, timezone
from pathlib import Path
from glob import glob

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
        try:
            if member.display_avatar:
                embed.set_thumbnail(url=member.display_avatar.url)
        except Exception:
            pass

        # Attach FibiLaugh from common locations (case-insensitive)
        file = None
        try:
            here = Path(__file__).resolve()
            roots = [here.parents[3], here.parents[2], here.parents[1]]  # project root, modules, discord_bot
            candidates = []
            for r in roots:
                if r and r.exists():
                    candidates += glob(str(r / "assets" / "*"))
            chosen = None
            for c in candidates:
                n = os.path.basename(c).lower()
                if n.startswith("fibilaugh") and n.split(".")[-1] in ("png","webp","jpg","jpeg","gif"):
                    chosen = c; break
            if chosen:
                fname = "fibilaugh" + os.path.splitext(chosen)[1]
                file = discord.File(chosen, filename=fname)
                embed.set_image(url=f"attachment://{fname}")
        except Exception:
            file = None

        if file:
            await ctx.send(embed=embed, file=file)
        else:
            await ctx.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(TestbanSim(bot))
