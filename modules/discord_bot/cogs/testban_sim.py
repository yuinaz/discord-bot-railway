from discord.ext import commands
import discord

class TestbanSim(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="testban", aliases=["tb"])
    async def testban(self, ctx: commands.Context, *, reason: str="Simulasi ban"):
        """Simulasi ban: tanpa target wajib. Menampilkan embed + gambar jika tersedia."""
        member = ctx.author
        from datetime import datetime, timezone
        embed = discord.Embed(
            title="Simulasi Ban oleh SatpamBot",
            description=f"{member.mention} terdeteksi mengirim pesan mencurigakan.\n*(Simulasi)*",
            color=discord.Color.orange(),
            timestamp=datetime.now(timezone.utc),
        )
        file = None
        try:
            from PIL import Image, ImageDraw, ImageFont
            from pathlib import Path
            import io
            base = Path(__file__).resolve().parents[3]
            candidates = [base / "assets" / "fibilaugh.png", base / "assets" / "fibilaugh.jpg", base / "static" / "fibilaugh.png"]
            img = None
            for p in candidates:
                if p.exists():
                    img = Image.open(p).convert("RGBA")
                    break
            if img is not None:
                w, h = img.size
                canvas = Image.new("RGBA", (max(900, w), 420), (24, 26, 32, 255))
                scale = 300 / max(1, max(img.size))
                img = img.resize((int(w*scale), int(h*scale)))
                canvas.paste(img, (canvas.width - img.width - 20, (canvas.height - img.height)//2), img)
                draw = ImageDraw.Draw(canvas)
                try:
                    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 24)
                except Exception:
                    font = ImageFont.load_default()
                draw.text((30, 40), "Simulasi Ban oleh SatpamBot", fill=(255,255,255,255), font=font)
                desc = ["[Simulasi testban]", "Pesan ini hanya simulasi untuk pengujian."]
                y = 90
                for line in desc:
                    draw.text((30, y), line, fill=(230,230,230,255), font=font); y += 34
                buf = io.BytesIO()
                canvas.save(buf, format="PNG"); buf.seek(0)
                file = discord.File(buf, filename="testban_sim.png")
                embed.set_image(url="attachment://testban_sim.png")
        except Exception:
            pass
        if file:
            await ctx.send(embed=embed, file=file)
        else:
            await ctx.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(TestbanSim(bot))
