# modules/discord_bot/cogs/moderation_test.py
from __future__ import annotations

import os as _os
from io import BytesIO
from pathlib import Path
from glob import glob
from datetime import datetime, timezone

import discord
from discord.ext import commands

# ==== OPSIONAL: Pillow untuk poster komposit ====
try:
    from PIL import Image, ImageDraw, ImageFont
except Exception:
    Image = None  # fallback ke banner biasa jika Pillow tak ada

# ==== CONFIG: channel notifikasi BAN (default ke ngobrol) ====
BAN_LOG_CHANNEL_ID = int(_os.getenv("BAN_LOG_CHANNEL_ID", "886534544688308265") or "0")
BAN_LOG_CHANNEL_NAME = _os.getenv("BAN_LOG_CHANNEL_NAME", "💬︲ngobrol")

MOD_ROLE_NAMES = {"mod", "moderator", "admin", "administrator", "staff"}

def is_moderator(member: discord.Member) -> bool:
    gp = member.guild_permissions
    if gp.administrator or gp.manage_guild or gp.ban_members or gp.kick_members or gp.manage_messages:
        return True
    role_names = {r.name.lower() for r in getattr(member, "roles", [])}
    return any(n in role_names for n in MOD_ROLE_NAMES)

def _resolve_ban_log_channel(ctx_or_guild) -> discord.TextChannel | None:
    g = getattr(ctx_or_guild, "guild", None) or ctx_or_guild
    if not g: return None
    if BAN_LOG_CHANNEL_ID:
        ch = g.get_channel(BAN_LOG_CHANNEL_ID)
        if isinstance(ch, discord.TextChannel): return ch
    for ch in g.text_channels:
        try:
            if ch.name == BAN_LOG_CHANNEL_NAME or ch.mention == BAN_LOG_CHANNEL_NAME:
                return ch
        except Exception:
            pass
    ch = getattr(ctx_or_guild, "channel", None)
    return ch if isinstance(ch, discord.TextChannel) else None

# === POSTER FIBI dgn AUTO-WRAP + AUTO-RESIZE (satu gambar di embed) ===
def _compose_fibi_poster(title: str, subtitle: str, badge: str, footnote: str = ""):
    """Return (discord.File, 'attachment://name') atau (None, None) kalau gagal."""
    if Image is None:
        return (None, None)
    try:
        assets = glob(str(Path(__file__).resolve().parents[3] / "assets" / "fibilaugh*"))
        if not assets: return (None, None)
        src = assets[0]
        im = Image.open(src).convert("RGBA")

        W = min(1024, im.width)
        H = int(im.height * (W / im.width))
        im = im.resize((W, H))
        draw = ImageDraw.Draw(im)

        def _font(sz):
            for fpath in ("DejaVuSans.ttf", "Arial.ttf", "arial.ttf"):
                try: return ImageFont.truetype(fpath, sz)
                except Exception: pass
            return ImageFont.load_default()

        def _text_size(txt, f):  # width,height
            bbox = draw.textbbox((0, 0), txt, font=f)
            return bbox[2] - bbox[0], bbox[3] - bbox[1]

        def _wrap_pixels(text, f, maxw):
            words = text.split()
            lines, cur = [], ""
            for w in words:
                test = (cur + " " + w).strip()
                if _text_size(test, f)[0] <= maxw:
                    cur = test
                else:
                    if cur: lines.append(cur)
                    cur = w
            if cur: lines.append(cur)
            return lines

        def _draw_multiline(left_x, top_y, lines, f, fill, outline=True, line_gap=8):
            y = top_y
            for line in lines:
                w, h = _text_size(line, f)
                if outline:
                    for ox, oy in ((2,0),(-2,0),(0,2),(0,-2)):
                        draw.text((left_x+ox, y+oy), line, font=f, fill=(0,0,0,160))
                draw.text((left_x, y), line, font=f, fill=fill)
                y += h + line_gap
            return y

        # Overlay gradasi gelap di atas agar kontras
        grad = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        gdraw = ImageDraw.Draw(grad)
        grad_h = int(H * 0.42)
        for i in range(grad_h):
            alpha = int(160 * (1 - i / grad_h))
            gdraw.line([(0, i), (W, i)], fill=(0, 0, 0, alpha))
        im = Image.alpha_composite(im, grad)
        draw = ImageDraw.Draw(im)

        # Layout & margin
        M = int(W * 0.05)
        x = M
        y = int(H * 0.07)
        maxw = W - 2 * M

        # Title: auto-shrink + wrap
        size = 64
        while size >= 32:
            f = _font(size)
            lines = _wrap_pixels(title, f, maxw)
            total_h = sum(_text_size(line, f)[1] for line in lines) + (len(lines)-1)*8
            if total_h <= int(H * 0.22):
                f_title = f; title_lines = lines; break
            size -= 2
        else:
            f_title = _font(32); title_lines = _wrap_pixels(title, f_title, maxw)

        y = _draw_multiline(x, y, title_lines, f_title, (255,255,255,240), outline=True, line_gap=10)

        # Subtitle + footnote: auto-shrink + wrap
        para = subtitle + (("\n" + footnote) if footnote else "")
        size = 36
        while size >= 22:
            f = _font(size)
            lines = []
            for block in para.split("\n"):
                if not block.strip():
                    lines.append("")
                else:
                    lines += _wrap_pixels(block, f, maxw)
            total_h = sum(_text_size(line, f)[1] for line in lines if line) + (max(0, len(lines)-1))*6
            if y + total_h <= int(H * 0.45):
                f_sub = f; sub_lines = lines; break
            size -= 2
        else:
            f_sub = _font(22); sub_lines = []
        y = _draw_multiline(x, y, sub_lines, f_sub, (235,235,235,235), outline=True, line_gap=6)

        # Badge (auto-shrink)
        size = 32
        while size >= 18:
            f_badge = _font(size)
            bw, bh = _text_size(badge, f_badge)
            if bw + 36 <= maxw: break
            size -= 1
        bx, by = x, y + 10
        pad_x, pad_y, radius = 18, 10, 18
        draw.rounded_rectangle(
            [bx-10, by-6, bx + bw + pad_x*2 -10, by + bh + pad_y*2 -6],
            radius=radius, fill=(29, 185, 84, 220)
        )
        draw.text((bx + pad_x -10, by + pad_y - 2), badge, font=f_badge, fill=(255,255,255,240))

        bio = BytesIO(); im.save(bio, "PNG"); bio.seek(0)
        fname = "fibi_poster.png"
        return (discord.File(bio, filename=fname), f"attachment://{fname}")
    except Exception:
        return (None, None)

# === Fallback lama: sticker/asset langsung ke embed (kalau Pillow tak ada) ===
async def _apply_fibi_banner(ctx: commands.Context, embed: discord.Embed):
    file = None
    try:
        if getattr(ctx.guild, "stickers", None):
            for s in ctx.guild.stickers:
                if (getattr(s, "name", "") or "").lower().startswith("fibi") and getattr(s, "url", None):
                    embed.set_image(url=s.url); break
        if not getattr(getattr(embed, "image", None), "url", None):
            assets = glob(str(Path(__file__).resolve().parents[3] / "assets" / "fibilaugh*"))
            if assets:
                chosen = assets[0]
                fname = "fibilaugh" + _os.path.splitext(chosen)[1]
                file = discord.File(chosen, filename=fname)
                embed.set_image(url=f"attachment://{fname}")
    except Exception:
        file = None
    return file


class ModerationTest(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.start_time = datetime.now(timezone.utc)

    # === STATUS ===
    async def status_cmd(self, ctx: commands.Context):
        latency_ms = round(self.bot.latency * 1000) if self.bot.latency is not None else 0
        uptime = str((datetime.now(timezone.utc) - self.start_time)).split(".", 1)[0]
        embed = discord.Embed(
            title="📊 Status SatpamBot",
            description=f"SatpamBot online dan siap berjaga.\n⏱ Uptime: **{uptime}** · 📶 Latency: **{latency_ms} ms**",
            color=discord.Color.green(),
            timestamp=datetime.now(timezone.utc),
        )
        file = await _apply_fibi_banner(ctx, embed)
        await ctx.send(embed=embed, file=file if file else None)

    # === SERVER INFO ===
    @commands.command(name="serverinfo")
    async def serverinfo_cmd(self, ctx: commands.Context):
        g = ctx.guild
        if not g: return await ctx.send("Perintah ini hanya untuk server.")
        embed = discord.Embed(
            title=f"ℹ️ Info Server: {g.name}",
            description=(
                f"👥 Member: **{getattr(g, 'member_count', '?')}**\n"
                f"🆔 ID: **{g.id}**" + (f"\n👑 Pemilik: **{g.owner}**" if g.owner else "")
            ),
            color=discord.Color.blurple(),
            timestamp=datetime.now(timezone.utc),
        )
        try:
            if g.icon: embed.set_thumbnail(url=g.icon.url)
        except Exception: pass
        file = await _apply_fibi_banner(ctx, embed)
        await ctx.send(embed=embed, file=file if file else None)

    # === TESTBAN LEGACY (tetap ada) ===
    @commands.command(name="__testban_legacy_disabled")
    @commands.guild_only()
    async def testban_legacy_cmd(self, ctx: commands.Context, member: discord.Member = None, *, reason: str = "Simulasi ban untuk pengujian"):
        if not is_moderator(ctx.author):
            return await ctx.send("❌ Hanya moderator.")
        if member is None:
            return await ctx.send("Gunakan: `!testban @user [alasan]`")
        embed = discord.Embed(
            title="💀 Simulasi Ban oleh SatpamBot (Legacy)",
            description=f"{member.mention} terdeteksi mengirim pesan mencurigakan.\n📝 **Alasan:** {reason}\n*(Simulasi)*",
            color=discord.Color.orange(),
            timestamp=datetime.now(timezone.utc),
        )
        file = await _apply_fibi_banner(ctx, embed)
        await ctx.send(embed=embed, file=file if file else None)

    # === TESTBAN (poster style) — kirim di channel tempat command dipanggil ===
    @commands.command(name="testban", aliases=["tb"])
    @commands.guild_only()
    async def testban_cmd(self, ctx: commands.Context, member: discord.Member = None, *, reason: str = "Simulasi ban untuk pengujian"):
        if not is_moderator(ctx.author):
            return await ctx.send("❌ Hanya moderator.")
        target = member or ctx.author

        title = "Simulasi Ban oleh SatpamBot"
        subtitle = f"{target.display_name} terdeteksi mengirim pesan mencurigakan."
        badge = "Simulasi testban"
        foot = "(Pesan ini hanya simulasi untuk pengujian.)"

        file, url = _compose_fibi_poster(title, subtitle, badge, footnote=foot)
        embed = discord.Embed(color=discord.Color.orange(), timestamp=datetime.now(timezone.utc))
        if file and url:
            embed.set_image(url=url)
        else:
            embed.title = title
            embed.description = f"{target.mention}\n*(Simulasi)*"
            f2 = await _apply_fibi_banner(ctx, embed)
            file = file or f2

        if _os.getenv("SHOW_THUMBNAIL", "0") in ("1", "true", "True"):
            try: embed.set_thumbnail(url=target.display_avatar.url)
            except Exception: pass

        await ctx.send(embed=embed, file=file if file else None)

    # === BAN (poster style dikirim ke channel ngobrol, lalu eksekusi) ===
    @commands.command(name="ban")
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    async def ban_cmd(self, ctx: commands.Context, member: discord.Member = None, *, reason: str = "Melanggar aturan"):
        if member is None:
            return await ctx.send("Gunakan: `!ban @user [alasan]`")
        if member == ctx.author:
            return await ctx.send("Tidak bisa ban diri sendiri.")

        log_ch = _resolve_ban_log_channel(ctx)
        title = "Ban oleh SatpamBot"
        subtitle = f"{member.display_name} telah dibanned dari server."
        badge = "Ban dieksekusi"

        file, url = _compose_fibi_poster(title, subtitle, badge)
        embed = discord.Embed(color=discord.Color.red(), timestamp=datetime.now(timezone.utc))
        if file and url:
            embed.set_image(url=url)
        else:
            embed.title = title
            embed.description = member.mention
            f2 = await _apply_fibi_banner(ctx, embed)
            file = file or f2

        await (log_ch or ctx).send(embed=embed, file=file if file else None)

        try:
            await member.ban(reason=reason, delete_message_days=0)
        except discord.Forbidden:
            return await ctx.send("❌ Aku tidak punya izin untuk memban user ini.")
        except Exception as e:
            return await ctx.send(f"❌ Gagal memban: {e}")

    # === UNBAN (notif ke channel ngobrol; poster style juga) ===
    async def unban_cmd(self, ctx: commands.Context, *, target: str):
        if not target:
            return await ctx.send("Gunakan: `!unban <user_id | username#1234>`")
        guild = ctx.guild

        async def find_user_to_unban():
            if target.isdigit():
                try:
                    u = await self.bot.fetch_user(int(target))
                    if u: return u
                except Exception: pass
            if "#" in target:
                name, discrim = target.rsplit("#", 1)
                for entry in await guild.bans():
                    u = entry.user
                    if (u.name == name and u.discriminator == discrim) or (f"{u.name}#{u.discriminator}".lower()==target.lower()):
                        return u
            for entry in await guild.bans():
                if str(entry.user.id) == target:
                    return entry.user
            return None

        user = await find_user_to_unban()
        if not user:
            return await ctx.send("❌ User tidak ditemukan dalam daftar ban.")
        try:
            await guild.unban(user, reason=f"Unban by {ctx.author}")
        except discord.Forbidden:
            return await ctx.send("❌ Aku tidak punya izin untuk unban.")
        except Exception as e:
            return await ctx.send(f"❌ Gagal unban: {e}")

        title = "Unban oleh SatpamBot"
        subtitle = f"{getattr(user, 'name', str(user))} di-unban dari server."
        badge = "Unban berhasil"
        file, url = _compose_fibi_poster(title, subtitle, badge)

        embed = discord.Embed(color=discord.Color.green(), timestamp=datetime.now(timezone.utc))
        if file and url:
            embed.set_image(url=url)
        else:
            embed.title = title
            f2 = await _apply_fibi_banner(ctx, embed)
            file = file or f2

        log_ch = _resolve_ban_log_channel(ctx)
        await (log_ch or ctx).send(embed=embed, file=file if file else None)


async def setup(bot: commands.Bot):
    cog = ModerationTest(bot)
    await bot.add_cog(cog)
    # proxy supaya tak bentrok
    async def _status_proxy(ctx: commands.Context, *a, **k): await cog.status_cmd(ctx, *a, **k)
    async def _unban_proxy(ctx: commands.Context, *a, **k): await cog.unban_cmd(ctx, *a, **k)
    try: bot.add_command(commands.Command(_status_proxy, name="status"))
    except commands.CommandRegistrationError:
        try: bot.add_command(commands.Command(_status_proxy, name="status_mtest", aliases=["status2","mstatus"]))
        except Exception: pass
    try: bot.add_command(commands.Command(_unban_proxy, name="unban"))
    except commands.CommandRegistrationError:
        try: bot.add_command(commands.Command(_unban_proxy, name="unban_mtest", aliases=["unban2","munban"]))
        except Exception: pass
