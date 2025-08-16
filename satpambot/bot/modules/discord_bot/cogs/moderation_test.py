from __future__ import annotations

import discord
from discord.ext import commands
from io import BytesIO
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter
    PIL_OK = True
except Exception:
    PIL_OK = False

CARD_W, CARD_H = 1200, 628  # ubah kalau perlu

# ---------- utils ----------
def _load_font(size: int, bold: bool = False):
    if not PIL_OK:
        return None
    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf", size)
    except Exception:
        return ImageFont.load_default()

def _find_fibi_asset() -> Path | None:
    here = Path(__file__).resolve()
    roots = [p for i, p in enumerate(here.parents) if i < 6] + [Path.cwd()]
    for r in roots:
    return None
    return None

def _text_len(draw: ImageDraw.ImageDraw, text: str, font) -> float:
    # kompatibel untuk berbagai versi PIL
    try:
        return draw.textlength(text, font=font)  # PIL>=9
    except Exception:
        try:
            return font.getlength(text)          # PIL>=10
        except Exception:
            bbox = draw.textbbox((0, 0), text, font=font)
            return float(bbox[2] - bbox[0])

def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_w: int):
    words = (text or "").split()
    lines, cur = [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if _text_len(draw, test, font) <= max_w or not cur:
            cur = test
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    if not lines:
        lines = [""]
    return lines

def _draw_text_block(draw: ImageDraw.ImageDraw, x: int, y: int, text: str, font, max_w: int,
                     fill="white", line_gap: int = 8, stroke=2):
    lines = _wrap(draw, text, font, max_w)
    for line in lines:
        # stroke untuk keterbacaan di atas gambar
        draw.text((x, y), line, font=font, fill=fill, stroke_width=stroke, stroke_fill=(0, 0, 0, 180))
        y += (font.size if hasattr(font, "size") else 32) + line_gap
    return y

# ---------- compositor ----------
def _compose_poster(username: str, mode: str = "testban") -> BytesIO:
    """
    Gambar tampil FULL (contain, tanpa crop) di atas background blur “cover”.
    Teks auto-wrap mengikuti lebar layout.
    """
    if not PIL_OK:
        raise RuntimeError("Pillow belum terpasang. Install pillow.")
    src = _find_fibi_asset()
    if not src or not src.exists():
        return None

    W, H = CARD_W, CARD_H

    # 1) Background: cover + blur + gelapkan
    img = Image.open(src).convert("RGB")
    bg_cover = ImageOps.fit(img, (W, H), method=Image.LANCZOS, centering=(0.5, 0.5))
    bg_cover = bg_cover.filter(ImageFilter.GaussianBlur(18))
    bg = bg_cover.convert("RGBA")
    dark = Image.new("RGBA", (W, H), (0, 0, 0, 90))
    bg.alpha_composite(dark)

    # 2) Foreground: contain (FULL tanpa crop)
    iw, ih = img.size
    scale = min(W / iw, H / ih)
    fw, fh = max(1, int(iw * scale)), max(1, int(ih * scale))
    fg = img.resize((fw, fh), Image.LANCZOS)
    fx, fy = (W - fw) // 2, (H - fh) // 2
    card = bg.copy()
    card.paste(fg, (fx, fy))

    # 3) Overlay tipis agar teks kontras
    veil = Image.new("RGBA", (W, H), (0, 0, 0, 70))
    card.alpha_composite(veil)

    draw = ImageDraw.Draw(card)
    title_font = _load_font(68, True)
    body_font = _load_font(36, False)
    note_font = _load_font(30, False)

    # 4) Badge
    chip = "Simulasi testban" if mode == "testban" else "Ban otomatis"
    chip_w = int(_text_len(draw, chip, body_font) + 48)
    chip_h = 56
    draw.rounded_rectangle((40, 40, 40 + chip_w, 40 + chip_h), radius=18,
                           fill=(34, 197, 94, 230) if mode == "testban" else (239, 68, 68, 230))
    draw.text((64, 40 + chip_h / 2 - (body_font.size / 2 if hasattr(body_font, 'size') else 18)),
              chip, font=body_font, fill="white")

    # 5) Text block dengan auto-wrap
    margin_x = 40
    text_max_w = W - margin_x * 2  # wrap mengikuti lebar kartu
    y = 140
    title = "Simulasi Ban oleh SatpamBot" if mode == "testban" else "Ban oleh SatpamBot"
    y = _draw_text_block(draw, margin_x, y, title, title_font, text_max_w, fill="white", line_gap=10, stroke=3)

    body = f"{username} terdeteksi mengirim pesan mencurigakan."
    y = _draw_text_block(draw, margin_x, y + 4, body, body_font, text_max_w, fill="white", line_gap=8, stroke=2)

    note = "(Pesan ini hanya simulasi untuk pengujian.)" if mode == "testban" else "(Penindakan otomatis oleh SatpamBot.)"
    _ = _draw_text_block(draw, margin_x, y + 2, note, note_font, text_max_w, fill=(235, 235, 235, 255), line_gap=6, stroke=2)

    # output
    out = BytesIO()
    card.convert("RGB").save(out, format="PNG", optimize=True)
    out.seek(0)
    return out

# ---------- Cog ----------
class ModerationTest(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="testban", aliases=["tb"])
    async def testban_cmd(self, ctx: commands.Context, *, target: discord.Member | str | None = None):
        username = target.display_name if isinstance(target, discord.Member) else (target or ctx.author.display_name)
        buf = _compose_poster(username=username, mode="testban")
        embed = discord.Embed(colour=discord.Colour.green(), description="(Simulasi)")
        await ctx.send(file=file, embed=embed)

    @commands.command(name="ban", aliases=["banpreview", "bp"])
    @commands.has_permissions(ban_members=True)
    async def ban_cmd(self, ctx: commands.Context, *, target: discord.Member | str | None = None):
        username = target.display_name if isinstance(target, discord.Member) else (target or ctx.author.display_name)
        buf = _compose_poster(username=username, mode="ban")
        embed = discord.Embed(colour=discord.Colour.red())
        await ctx.send(file=file, embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(ModerationTest(bot))
