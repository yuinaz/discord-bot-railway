import discord
from discord.ext import commands
from datetime import datetime, timezone
from PIL import Image, ImageDraw, ImageFont
import io, os
from typing import Optional
from pathlib import Path

MOD_ROLE_NAMES = {"mod", "moderator", "admin", "administrator", "staff"}

def is_moderator(member: discord.Member) -> bool:
    gp = member.guild_permissions
    if gp.administrator or gp.manage_guild or gp.ban_members or gp.kick_members or gp.manage_messages:
        return True
    role_names = {r.name.lower() for r in getattr(member, "roles", [])}
    return any(n in role_names for n in MOD_ROLE_NAMES)

def _load_font(pref_list, size):
    for path in pref_list:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()

async def _get_fibilaugh_image(ctx):
    """Cari file lokal FibiLaugh dengan path absolut supaya aman di Render."""
    # __file__ = modules/discord_bot/cogs/moderation_extras.py
    # Naik 3x -> project root
    base = Path(__file__).resolve().parents[3]
    candidates = [
        base / "assets" / "fibilaugh.png",
        base / "assets" / "fibilaugh.jpg",
        base / "assets" / "fibilaugh.webp",
        base / "static" / "fibilaugh.png",
    ]
    for p in candidates:
        try:
            if p.exists():
                return Image.open(p).convert("RGBA")
        except Exception:
            continue
    return None

def _compose_card(title, desc_lines, badge_text, reason_line, sticker_img=None, width=900, height=420, badge_color=(40, 167, 69)):
    bg = (24, 26, 32)
    text_primary = (255, 255, 255)
    text_secondary = (220, 220, 220)
    text_warn = (255, 230, 170)

    img = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(img)

    font_title = _load_font([
        "C:/Windows/Fonts/arialbd.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/SFNSRounded.ttf",
    ], 36)
    font_text = _load_font([
        "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/SFNS.ttf",
    ], 24)

    x, y = 30, 30
    draw.text((x, y), title, fill=text_primary, font=font_title)
    y += 56
    for line in desc_lines:
        draw.text((x, y), line, fill=text_secondary, font=font_text)
        y += 32
    y += 10

    badge_w, badge_h = 320, 40
    draw.rounded_rectangle([x, y, x + badge_w, y + badge_h], radius=10, fill=badge_color)
    by = y + (badge_h - 28) // 2
    draw.text((x + 12, by), badge_text, fill=text_primary, font=font_text)
    y += badge_h + 18
    draw.text((x, y), reason_line, fill=text_warn, font=font_text)

    if sticker_img:
        max_w, max_h = 360, 360
        s = sticker_img.copy()
        s.thumbnail((max_w, max_h))
        sx = width - s.width - 30
        sy = 30
        try:
            img.paste(s, (sx, sy), s)
        except Exception:
            img.paste(s, (sx, sy))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf

class ModerationExtras(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="testban", aliases=["tb"])
    @commands.guild_only()
    async def testban_cmd(
        self,
        ctx: commands.Context,
        member: Optional[discord.Member] = None,
        *,
        reason: str = "Simulasi ban untuk pengujian",
    ):
        if not is_moderator(ctx.author):
            return await ctx.send("❌ Hanya moderator yang dapat menggunakan perintah ini.")
        if member is None:
            member = ctx.author

        title = "💀 Simulasi Ban oleh SatpamBot"
        desc_lines = [
            f"{member.display_name} terdeteksi mengirim pesan mencurigakan.",
            "(Pesan ini hanya simulasi untuk pengujian.)",
        ]
        reason_line = f"📝 {reason}"
        sticker_img = await _get_fibilaugh_image(ctx)
        buf = _compose_card(
            title, desc_lines, "✅ Simulasi testban", reason_line,
            sticker_img=sticker_img, badge_color=(40, 167, 69)
        )

        file = discord.File(buf, filename="testban_card.png")
        embed = discord.Embed(
            title="Simulasi Ban oleh SatpamBot",
            description=f"{member.mention} terdeteksi mengirim pesan mencurigakan.\n*(Simulasi)*",
            color=discord.Color.orange(),
            timestamp=datetime.now(timezone.utc),
        )
        embed.set_image(url="attachment://testban_card.png")
        try:
            if member.display_avatar:
                embed.set_thumbnail(url=member.display_avatar.url)
        except Exception:
            pass
        await ctx.send(embed=embed, file=file)

    @commands.command(name="sbfibi_check")
    async def sbfibi_check(self, ctx: commands.Context):
        base = Path(__file__).resolve().parents[3]
        p = base / "assets" / "fibilaugh.png"
        await ctx.send(f"{p} => {'ADA' if p.exists() else 'TIDAK ADA'}")

    @commands.command(name="sbdiag")
    async def sbdiag(self, ctx: commands.Context):
        try:
            import inspect
            src = inspect.getsourcefile(self.__class__)
        except Exception:
            src = __file__
        await ctx.send(f"[sbdiag] moderation_extras loaded from: {src}")

async def setup(bot: commands.Bot):
    await bot.add_cog(ModerationExtras(bot))
