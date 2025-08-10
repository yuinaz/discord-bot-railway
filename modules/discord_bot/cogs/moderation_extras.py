import discord
from discord.ext import commands
from datetime import datetime, timezone
from PIL import Image, ImageDraw, ImageFont
import io, os
from typing import Optional

# === Konfigurasi Sticker ===
FIBILaugh_STICKER_ID = 1373959100496351283  # ganti bila ID di server berbeda

MOD_ROLE_NAMES = {"mod", "moderator", "admin", "administrator", "staff"}

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

async def _resolve_fibilaugh_sticker(ctx) -> Optional[discord.GuildSticker]:
    """Balikkan GuildSticker FibiLaugh (prefer ID, lalu nama)."""
    g = ctx.guild
    if not g:
        return None
    # 1) by ID
    if FIBILaugh_STICKER_ID:
        try:
            st = await g.fetch_sticker(FIBILaugh_STICKER_ID)
            return st
        except Exception:
            pass
    # 2) by name (cache + fetch)
    try:
        st = discord.utils.get(getattr(g, "stickers", []), name="FibiLaugh")
        if st:
            return st
    except Exception:
        pass
    try:
        fetched = await g.fetch_stickers()
        for s in fetched:
            if (getattr(s, "name", "") or "").lower().replace("-", " ") in {"fibilaugh","fibi laugh","fibi_laugh"}:
                return s
    except Exception:
        pass
    return None

async def _get_fibilaugh_image(ctx):
    """Gambar komposit fallback untuk kartu; pakai file lokal bila ada.
       (Sticker animasi tidak bisa dirender PIL; sticker tetap dikirim native via 'stickers=[...]').
    """
    for p in ("assets/fibilaugh.png", "assets/fibilaugh.jpg", "assets/fibilaugh.webp", "static/fibilaugh.png"):
        if os.path.exists(p):
            try:
                return Image.open(p).convert("RGBA")
            except Exception:
                pass
    return None

def _compose_card(title, desc_lines, badge_text, reason_line, sticker_img=None, width=900, height=420, badge_color=(40, 167, 69)):
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
        "/System/Library/Fonts/SFNSRounded.ttf",
    ], 36)
    font_text = _load_font([
        "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/SFNS.ttf",
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
    draw.rounded_rectangle([x, y, x + badge_w, y + badge_h], radius=10, fill=badge_color)
    by = y + (badge_h - 28) // 2
    draw.text((x + 12, by), badge_text, fill=text_primary, font=font_text)
    y += badge_h + 18
    draw.text((x, y), reason_line, fill=text_warn, font=font_text)

    # Sticker (right) — hanya bila ada fallback image
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
            timestamp=datetime.now(timezone.utc),
        )
        embed.add_field(name="Server ID", value=str(g.id), inline=True)
        embed.add_field(name="Owner", value=getattr(g.owner, "mention", "Unknown"), inline=True)
        embed.add_field(name="Members", value=str(g.member_count), inline=True)
        embed.add_field(name="Created", value=g.created_at.strftime("%Y-%m-%d %H:%M UTC"), inline=True)
        if g.icon:
            embed.set_thumbnail(url=g.icon.url)
        await ctx.send(embed=embed)

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
        sticker_img = await _get_fibilaugh_image(ctx)  # untuk komposit (opsional)
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

        # --- Kirim sticker native juga (selalu tampil walau animasi) ---
        sticker_obj = await _resolve_fibilaugh_sticker(ctx)
        try:
            if sticker_obj:
                await ctx.send(embed=embed, file=file, stickers=[sticker_obj])
                return
        except Exception:
            pass

        # Fallback: kirim tanpa sticker kalau tidak bisa
        await ctx.send(embed=embed, file=file)

    @commands.command(name="ban")
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    async def ban_cmd(self, ctx: commands.Context, member: Optional[discord.Member] = None, *, reason: str = "Melanggar aturan"):
        if member is None:
            member = ctx.author
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
            timestamp=datetime.now(timezone.utc),
        )
        embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
        embed.add_field(name="Alasan", value=reason, inline=False)
        embed.set_image(url="attachment://ban_card.png")

        sticker_obj = await _resolve_fibilaugh_sticker(ctx)
        try:
            if sticker_obj:
                await ctx.send(embed=embed, file=file, stickers=[sticker_obj])
                return
        except Exception:
            pass
        await ctx.send(embed=embed, file=file)

    @commands.command(name="sbstickers")
    async def sbstickers(self, ctx: commands.Context):
        """List sticker yang terlihat bot (untuk debug)."""
        try:
            fetched = await ctx.guild.fetch_stickers()
            names = [f"{getattr(s, 'name', f'id:{s.id}')}({s.id})" for s in fetched]
            if names:
                await ctx.send("Stickers: " + ", ".join(names[:50]))
            else:
                await ctx.send("Tidak ada sticker ter-fetch (atau izin kurang).")
        except Exception as e:
            await ctx.send(f"Sticker fetch error: {e}")

    @commands.command(name="sbstickerid")
    async def sbstickerid(self, ctx: commands.Context):
        """Cek ambil sticker via ID langsung."""
        try:
            st = await ctx.guild.fetch_sticker(FIBILaugh_STICKER_ID)
            fmt = getattr(st, "format", None) or getattr(st, "format_type", None)
            await ctx.send(f"StickerID OK: {st.name} | id={st.id} | format={fmt}")
        except Exception as e:
            await ctx.send(f"Gagal fetch sticker ID: {e}")

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
