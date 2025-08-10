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
    from pathlib import Path
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
    # Base canvas (RGBA so we can alpha-composite)
    bg_color = (24, 26, 32)
    img = Image.new("RGBA", (width, height), bg_color + (255,))

    # Use fibilaugh as background when available
    if sticker_img:
        bg = sticker_img.convert("RGBA").copy()
        ratio = max(width / bg.width, height / bg.height)
        new_size = (int(bg.width * ratio), int(bg.height * ratio))
        bg = bg.resize(new_size, Image.LANCZOS)
        # center crop
        left = (bg.width - width) // 2
        top = (bg.height - height) // 2
        bg = bg.crop((left, top, left + width, top + height))
        img.paste(bg, (0, 0))
        # dark overlay for text readability
        overlay = Image.new("RGBA", (width, height), (0, 0, 0, 140))
        img = Image.alpha_composite(img, overlay)

    draw = ImageDraw.Draw(img)

    # Fonts
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

    white = (255, 255, 255)
    secondary = (230, 230, 230)
    accent = (255, 230, 170)

    # Text
    x, y = 30, 30
    draw.text((x, y), title, fill=white, font=font_title)
    y += 56
    for line in desc_lines:
        draw.text((x, y), line, fill=secondary, font=font_text)
        y += 32
    y += 10

    # Badge
    badge_w, badge_h = 320, 40
    try:
        draw.rounded_rectangle([x, y, x + badge_w, y + badge_h], radius=10, fill=badge_color)
    except Exception:
        draw.rectangle([x, y, x + badge_w, y + badge_h], fill=badge_color)
    by = y + (badge_h - 28) // 2
    draw.text((x + 12, by), badge_text, fill=white, font=font_text)
    y += badge_h + 18

    draw.text((x, y), reason_line, fill=accent, font=font_text)

    # Export
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG")
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
