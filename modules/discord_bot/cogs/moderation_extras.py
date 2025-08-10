import discord
from discord.ext import commands
from datetime import datetime, timezone
from PIL import Image, ImageDraw, ImageFont
import io, os

MOD_ROLE_NAMES = {"mod","moderator","admin","administrator","staff"}

def is_moderator(member: discord.Member) -> bool:
    gp = member.guild_permissions
    if gp.administrator or gp.manage_guild or gp.ban_members or gp.kick_members or gp.manage_messages:
        return True
    role_names = {r.name.lower() for r in getattr(member, "roles", [])}
    return any(n in role_names for n in MOD_ROLE_NAMES)

# ---- helpers ----
def _load_font(pref_list, size):
    for path in pref_list:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()

async def _get_fibilaugh_image(ctx):
    # Try sticker in guild
    sticker = None
    try:
        sticker = discord.utils.find(lambda s: getattr(s, "name", "").lower() == "fibilaugh", getattr(ctx.guild, "stickers", []))
    except Exception:
        sticker = None
    if sticker:
        try:
            asset = getattr(sticker, "url", None)
            if asset:
                data = await asset.read()
                import io as _io
                from PIL import Image as _Image
                return _Image.open(_io.BytesIO(data)).convert("RGBA")
        except Exception:
            pass
    # Fallback local asset
    for p in ("assets/fibilaugh.png","assets/fibilaugh.jpg","assets/fibilaugh.webp","static/fibilaugh.png"):
        if os.path.exists(p):
            try:
                return Image.open(p).convert("RGBA")
            except Exception:
                continue
    return None

def _compose_card(title, desc_lines, badge_text, reason_line, sticker_img=None, width=900, height=420, badge_color=(40,167,69)):
    # Colors
    bg = (24, 26, 32)
    text_primary = (255, 255, 255)
    text_secondary = (220, 220, 220)
    text_warn = (255, 230, 170)

    img = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(img)

    # Fonts (common Windows/Linux/Mac fallbacks)
    font_title = _load_font([
        "C:/Windows/Fonts/arialbd.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/SFNSRounded.ttf"
    ], 36)
    font_text = _load_font([
        "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/SFNS.ttf"
    ], 24)

    # Text block (left)
    x, y = 30, 30
    draw.text((x, y), title, fill=text_primary, font=font_title)
    y += 56
    for line in desc_lines:
        draw.text((x, y), line, fill=text_secondary, font=font_text)
        y += 32
    y += 10
    # badge
    badge_w, badge_h = 320, 40
    draw.rounded_rectangle([x, y, x+badge_w, y+badge_h], radius=10, fill=badge_color)
    by = y + (badge_h - 28)//2
    draw.text((x+12, by), badge_text, fill=text_primary, font=font_text)
    y += badge_h + 18
    draw.text((x, y), reason_line, fill=text_warn, font=font_text)

    # Sticker (right)
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

    @commands.command(name="serverinfo")
    async def serverinfo_cmd(self, ctx: commands.Context):
        g = ctx.guild
        if not g:
            return await ctx.send("Perintah ini hanya untuk server.")
        embed = discord.Embed(
            title=f"Server Info — {g.name}",
            color=discord.Color.blurple(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="Server ID", value=str(g.id), inline=True)
        embed.add_field(name="Owner", value=getattr(g.owner, 'mention', 'Unknown'), inline=True)
        embed.add_field(name="Members", value=str(g.member_count), inline=True)
        embed.add_field(name="Created", value=g.created_at.strftime("%Y-%m-%d %H:%M UTC"), inline=True)
        if g.icon: embed.set_thumbnail(url=g.icon.url)
        await ctx.send(embed=embed)

    @commands.command(name="testban")
    @commands.guild_only()
    async def testban_cmd(self, ctx: commands.Context, member: discord.Member=None, *, reason: str = "Simulasi ban untuk pengujian"):
        if not is_moderator(ctx.author):
            return await ctx.send("❌ Hanya moderator yang dapat menggunakan perintah ini.")
        if member is None:
            return await ctx.send("Gunakan: `!testban @user [alasan]`")

        title = "💀 Simulasi Ban oleh SatpamBot"
        desc_lines = [f"{member.display_name} terdeteksi mengirim pesan mencurigakan.",
                      "(Pesan ini hanya simulasi untuk pengujian.)"]
        reason_line = f"📝 {reason}"
        sticker_img = await _get_fibilaugh_image(ctx)
        buf = _compose_card(title, desc_lines, "✅ Simulasi testban", reason_line, sticker_img=sticker_img, badge_color=(40,167,69))

        file = discord.File(buf, filename="testban_card.png")
        embed = discord.Embed(
            title="Simulasi Ban oleh SatpamBot",
            description=f"{member.mention} terdeteksi mengirim pesan mencurigakan.\n*(Simulasi)*",
            color=discord.Color.orange(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.set_image(url="attachment://testban_card.png")
        try:
            if member.display_avatar:
                embed.set_thumbnail(url=member.display_avatar.url)
        except Exception:
            pass
        await ctx.send(embed=embed, file=file)

    @commands.command(name="ban")
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    async def ban_cmd(self, ctx: commands.Context, member: discord.Member=None, *, reason: str = "Melanggar aturan"):
        if member is None:
            return await ctx.send("Gunakan: `!ban @user [alasan]`")
        if member == ctx.author:
            return await ctx.send("Tidak bisa ban diri sendiri.")
        try:
            await member.ban(reason=reason, delete_message_days=0)
        except discord.Forbidden:
            return await ctx.send("❌ Aku tidak punya izin untuk memban user ini.")
        except Exception as e:
            return await ctx.send(f"❌ Gagal memban: {e}")

        title = "🚫 User Dibanned"
        desc_lines = [f"{member.display_name} telah dibanned.", "Aksi dilakukan oleh moderator."]
        reason_line = f"📝 {reason}"
        sticker_img = await _get_fibilaugh_image(ctx)
        buf = _compose_card(title, desc_lines, "🔨 Ban", reason_line, sticker_img=sticker_img, badge_color=(220, 53, 69))

        file = discord.File(buf, filename="ban_card.png")
        embed = discord.Embed(
            title="User Dibanned",
            description=f"{member.mention} telah dibanned.",
            color=discord.Color.red(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
        embed.add_field(name="Alasan", value=reason, inline=False)
        embed.set_image(url="attachment://ban_card.png")
        try:
            if member.display_avatar:
                embed.set_thumbnail(url=member.display_avatar.url)
        except Exception:
            pass
        await ctx.send(embed=embed, file=file)

async def setup(bot: commands.Bot):
    await bot.add_cog(ModerationExtras(bot))
