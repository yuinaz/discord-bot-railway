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
        file=None
        try:
            from PIL import Image, ImageDraw, ImageFont; from pathlib import Path; import io
            base = Path(__file__).resolve().parents[3]
            for p in [base/'assets'/'fibilaugh.png', base/'assets'/'fibilaugh.jpg', base/'static'/'fibilaugh.png']:
                if p.exists():
                    img = Image.open(p).convert("RGBA"); break
            else:
                img=None
            if img is not None:
                W,H=900,420; canvas=Image.new("RGBA",(W,H),(24,26,32,255))
                scale = 360/max(1,max(img.size)); img = img.resize((int(img.width*scale), int(img.height*scale)))
                canvas.paste(img,(W-img.width-20,(H-img.height)//2),img)
                draw=ImageDraw.Draw(canvas)
                try: font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",24)
                except Exception: font=ImageFont.load_default()
                draw.text((30,40),"Simulasi Ban oleh SatpamBot",fill=(255,255,255,255),font=font)
                draw.text((30,90),f"Target: {member}",fill=(230,230,230,255),font=font)
                draw.text((30,130),f"Alasan: {reason}",fill=(230,230,230,255),font=font)
                buf=io.BytesIO(); canvas.save(buf, format="PNG"); buf.seek(0)
                file=discord.File(buf, filename="testban_sim.png"); embed.set_image(url="attachment://testban_sim.png")
        except Exception: pass
        if file: await ctx.send(embed=embed, file=file)
        else: await ctx.send(embed=embed)

async def setup(bot: commands.Bot): await bot.add_cog(TestbanSim(bot))
