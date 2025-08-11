from discord.ext import commands
import discord

DARK_BG = (24, 26, 32, 255)
OVERLAY = (0, 0, 0, 120)
WHITE = (255, 255, 255, 255)
SECONDARY = (230, 230, 230, 255)
ACCENT = (255, 230, 170, 255)
GREEN = (40, 167, 69, 255)

class TestbanSim(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    def _load_font(self, size):
        try:
            from PIL import ImageFont
        except Exception:
            return None
        for path in [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/System/Library/Fonts/SFNS.ttf",
            "C:/Windows/Fonts/arial.ttf",
        ]:
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
        try:
            return ImageFont.load_default()
        except Exception:
            return None

    def _compose_card(self, title: str, desc_lines, badge_text: str, reason_line: str):
        try:
            from PIL import Image, ImageDraw, ImageFont
            from pathlib import Path
            import io
        except Exception:
            return None, None

        W, H = 900, 420
        img = Image.new("RGBA", (W, H), DARK_BG)
        draw = ImageDraw.Draw(img)

        # Try sticker image (FibiLaugh) as background element (right side)
        sticker = None
        try:
            base = Path(__file__).resolve().parents[3]
            for p in [base/'assets'/'fibilaugh.png', base/'assets'/'fibilaugh.jpg', base/'static'/'fibilaugh.png']:
                if p.exists():
                    from PIL import Image as _Image
                    sticker = _Image.open(p).convert("RGBA")
                    break
        except Exception:
            sticker = None

        if sticker is not None:
            # Resize to fit height ~360 and place at center-right
            scale = 360 / max(1, max(sticker.size))
            nw, nh = int(sticker.width*scale), int(sticker.height*scale)
            sticker = sticker.resize((nw, nh))
            x = W - nw - 20
            y = (H - nh)//2
            img.paste(sticker, (x, y), sticker)

        # Glass overlay for text block (top-left region)
        draw.rounded_rectangle((16, 16, W-16, 140), radius=14, fill=OVERLAY)

        # Text
        font_title = self._load_font(28)
        font_body = self._load_font(20)
        font_badge = self._load_font(18)

        x, y = 32, 30
        if font_title:
            draw.text((x, y), title, fill=WHITE, font=font_title)
        else:
            draw.text((x, y), title, fill=WHITE)
        y += 42
        for line in desc_lines:
            if font_body:
                draw.text((x, y), line, fill=SECONDARY, font=font_body)
            else:
                draw.text((x, y), line, fill=SECONDARY)
            y += 28

        # Badge (green pill)
        bx, by = x, y + 8
        text = badge_text
        if font_badge:
            tw, th = draw.textlength(text, font=font_badge), font_badge.size + 6
        else:
            tw, th = draw.textlength(text), 24
        padx, pady = 14, 6
        draw.rounded_rectangle((bx, by, bx + int(tw) + 2*padx, by + th + 2*pady), radius=10, fill=GREEN)
        tx = bx + padx
        ty = by + pady
        if font_badge:
            draw.text((tx, ty), text, fill=WHITE, font=font_badge)
        else:
            draw.text((tx, ty), text, fill=WHITE)

        # Reason line (under badge)
        ry = by + th + 2*pady + 10
        if font_body:
            draw.text((x, ry), reason_line, fill=SECONDARY, font=font_body)
        else:
            draw.text((x, ry), reason_line, fill=SECONDARY)

        # Encode
        buf = io.BytesIO()
        img.save(buf, format="PNG"); buf.seek(0)
        return buf, "testban_card.png"

    @commands.command(name="testban", aliases=["tb"])
    async def testban(self, ctx: commands.Context, *, reason: str="Simulasi ban untuk percobaan"):
        member = ctx.author

        # Main embed, mirror the screenshot style
        embed = discord.Embed(
            title="Simulasi Ban oleh SatpamBot",
            description=f"{member.mention} terdeteksi mengirim pesan mencurigakan.\n*(Simulasi)*",
            color=discord.Color.orange(),
        )
        # Thumbnail = author avatar
        try:
            if member.display_avatar:
                embed.set_thumbnail(url=member.display_avatar.url)
        except Exception:
            pass

        file = None
        try:
            buf, filename = self._compose_card(
                "Simulasi Ban oleh SatpamBot",
                [f"{member.display_name} terdeteksi mengirim pesan mencurigakan.", "(Pesan ini hanya simulasi untuk pengujian.)"],
                "Simulasi testban",
                reason,
            )
            if buf:
                file = discord.File(buf, filename=filename)
                embed.set_image(url=f"attachment://{filename}")
        except Exception:
            pass

        if file:
            await ctx.send(embed=embed, file=file)
        else:
            await ctx.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(TestbanSim(bot))
