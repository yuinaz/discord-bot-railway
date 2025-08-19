from __future__ import annotations
import logging
from typing import Optional
import discord
from discord.ext import commands
from satpambot.bot.modules.discord_bot.utils.perm import require_mod
from satpambot.bot.modules.discord_bot.helpers.banlog_helper import get_banlog_thread, send_public_ban_announcement

log = logging.getLogger(__name__)
GREEN = 0x3BA55D
RED   = 0xED4245
YEL   = 0xFEE75C

async def _resolve_target(ctx: commands.Context, member: Optional[discord.Member]) -> Optional[discord.Member]:
    # direct arg
    if isinstance(member, discord.Member):
        return member
    # mentions
    if ctx.message.mentions:
        for m in ctx.message.mentions:
            if isinstance(m, discord.Member) and not m.bot:
                return m
    # reply reference
    ref = getattr(ctx.message, "reference", None)
    if ref:
        try:
            msg = None
            if getattr(ref, "resolved", None) and isinstance(ref.resolved, discord.Message):
                msg = ref.resolved
            elif getattr(ref, "message_id", None):
                msg = await ctx.channel.fetch_message(ref.message_id)
            if msg and isinstance(msg.author, discord.Member) and not msg.author.bot:
                return msg.author
        except Exception:
            pass
    # last human message
    try:
        async for m in ctx.channel.history(limit=20):
            if m.id == ctx.message.id:
                continue
            a = m.author
            if isinstance(a, discord.Member) and not a.bot:
                return a
    except Exception:
        pass
    return None

def _embed_sim_ok(target: discord.Member, moderator: discord.Member) -> discord.Embed:
    # Harus PERSIS seperti contoh pengguna
    title = "💀 Simulasi Ban oleh SatpamBot"
    desc  = f"{target.mention} terdeteksi mengirim pesan mencurigakan.\n\n(Pesan ini hanya simulasi untuk pengujian.)"
    e = discord.Embed(title=title, description=desc, color=YEL)
    # Garis kecil "Simulasi testban" sesuai contoh
    e.add_field(name="🏷️ Simulasi testban", value="\u200b", inline=False)
    e.set_footer(text=f"Moderator: {moderator}")
    return e

def _embed_sim_fail(target_text: str, why: str, moderator: discord.Member) -> discord.Embed:
    e = discord.Embed(
        title="❌ Simulasi Ban Gagal",
        description=f"{target_text} tidak dapat disimulasikan untuk diban.\n\nDetail: {why}",
        color=RED
    )
    e.set_footer(text=f"Moderator: {moderator}")
    return e

def _embed_banned(target: discord.Member, moderator: discord.Member) -> discord.Embed:
    e = discord.Embed(
        title="⛔ BANNED",
        description=f"{target.mention} telah diban.",
        color=GREEN
    )
    e.set_footer(text=f"Moderator: {moderator}")
    return e

def _can_act(me: discord.Member, target: discord.Member) -> tuple[bool, str]:
    if target.id == me.id:
        return False, "Tidak bisa ban diri sendiri."
    if target.guild.owner_id == target.id:
        return False, "Tidak bisa ban pemilik server."
    if me.top_role <= target.top_role:
        return False, "Role bot tidak lebih tinggi dari target."
    if not (me.guild_permissions.ban_members or me.guild_permissions.administrator):
        return False, "Bot tidak punya izin ban_members/administrator."
    return True, "OK"

class BanSecure(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _log(self, guild: discord.Guild, embed: discord.Embed):
        try:
            th = await get_banlog_thread(guild)
            if th:
                await th.send(embed=embed)
        except Exception as e:
            log.warning("Gagal tulis banlog: %s", e)

        @commands.command(name="tb", aliases=["testban"])
        @require_mod()
        @commands.guild_only()
        async def testban(self, ctx: commands.Context, member: Optional[discord.Member]=None, *, reason: str=""):
            # Guard duplicate trigger
            if not self._guard(ctx.message.id):
                return
            # Resolve target but DO NOT enforce hierarchy/permissions (simulation must always work)
            target = await _resolve_target(ctx, member)
            if not isinstance(target, discord.Member):
                # best-effort fallback to author (should rarely happen in guild)
                target = ctx.author if isinstance(ctx.author, discord.Member) else None

            try:
                em = _embed_sim_ok(target, ctx.author)
            except Exception:
                # As last resort, build a minimal embed without member-specific fields
                em = discord.Embed(
                    title="💀 Simulasi Ban oleh SatpamBot",
                    description=f"{getattr(target,'mention', 'Seorang pengguna')} terdeteksi mengirim pesan mencurigakan.\n(Pesan ini hanya simulasi untuk pengujian.)",
                    color=0x2F3136,
                )
                em.set_footer(text="Simulasi testban")

            await ctx.reply(embed=em, mention_author=False)
            await self._log(ctx.guild, em)@commands.command(name="ban")
    @require_mod()
    @commands.guild_only()
    @commands.has_guild_permissions(ban_members=True)
    async def ban(self, ctx: commands.Context, member: Optional[discord.Member]=None, *, reason: str=""):
        target = await _resolve_target(ctx, member)
        if not isinstance(target, discord.Member):
            return await ctx.reply("Tidak ada target. Format: `!ban @user [alasan]` atau **reply** pesan target lalu ketik `!ban`", mention_author=False)

        me = ctx.guild.me
        ok, why = _can_act(me, target)
        if not ok:
            em = _embed_sim_fail(getattr(target, "mention", str(target)), why, ctx.author)
            await ctx.reply(embed=em, mention_author=False)
            await self._log(ctx.guild, em)
            return
        try:
            await target.ban(reason=reason or f"Moderator: {ctx.author}")
            em = _embed_banned(target, ctx.author)
            await ctx.reply(embed=em, mention_author=False)
            await self._log(ctx.guild, em)
        except discord.Forbidden:
            em = _embed_sim_fail(target.mention, "Forbidden: izin bot kurang.", ctx.author)
            await ctx.reply(embed=em, mention_author=False)
            await self._log(ctx.guild, em)
        except discord.HTTPException as e:
            em = _embed_sim_fail(target.mention, f"HTTP: {e}", ctx.author)
            await ctx.reply(embed=em, mention_author=False)
            await self._log(ctx.guild, em)

async def setup(bot: commands.Bot):
    # Remove command lama yang mungkin nabrak
    for name in ("ban","tb","testban"):
        try:
            cmd = bot.get_command(name)
            if cmd:
                bot.remove_command(name)
        except Exception:
            pass
    await bot.add_cog(BanSecure(bot))
