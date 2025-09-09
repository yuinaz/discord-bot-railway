
from __future__ import annotations

import logging
from typing import Optional

import discord
from discord.ext import commands

try:
    # keep imports identical so other code stays happy
    from satpambot.bot.modules.discord_bot.utils.perm import require_mod
except Exception:
    # fallback: allow command if user has ban_members
    def require_mod():
        def decorator(func):
            async def predicate(ctx: commands.Context, *a, **kw):
                perms = getattr(ctx.author, "guild_permissions", None)
                if perms and (perms.ban_members or perms.administrator):
                    return await func(ctx, *a, **kw)
                raise commands.CheckFailure("Moderator permission required")
            return commands.check(lambda ctx: True)(predicate)  # simple wrapper
        return decorator

try:
    from satpambot.bot.modules.discord_bot.helpers.banlog_helper import get_banlog_thread, send_public_ban_announcement  # noqa: F401
except Exception:
    async def get_banlog_thread(guild):  # type: ignore
        return None
    async def send_public_ban_announcement(*a, **kw):  # type: ignore
        return None

log = logging.getLogger(__name__)
GREEN = 0x3BA55D
RED   = 0xED4245
YEL   = 0xFEE75C

async def _resolve_target(ctx: commands.Context, member: Optional[discord.Member]) -> Optional[discord.Member]:
    if isinstance(member, discord.Member):
        return member
    # reply target
    try:
        ref = ctx.message.reference
        if ref and ref.resolved and isinstance(ref.resolved, discord.Message):
            m = ref.resolved
            a = m.author
            if isinstance(a, discord.Member) and not a.bot:
                return a
    except Exception:
        pass
    # last non-bot in channel (excluding the command message)
    try:
        async for m in ctx.channel.history(limit=10):
            if m.id == ctx.message.id:
                continue
            a = m.author
            if isinstance(a, discord.Member) and not a.bot:
                return a
    except Exception:
        pass
    return None

def _embed_sim_ok(target: discord.Member, moderator: discord.Member) -> discord.Embed:
    title = "💀 Simulasi Ban oleh SatpamBot"
    desc  = f"{target.mention} terdeteksi mengirim pesan mencurigakan.\n\n(Pesan ini hanya simulasi untuk pengujian.)"
    e = discord.Embed(title=title, description=desc, color=YEL)
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

class BanSecure(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._recent = set()

    def _guard(self, msg_id: int) -> bool:
        if msg_id in self._recent:
            return False
        self._recent.add(msg_id)
        if len(self._recent) > 1000:
            self._recent = set(list(self._recent)[-1000:])
        return True

    async def _log(self, guild: discord.Guild, embed: discord.Embed):
        try:
            th = await get_banlog_thread(guild)
            if th:
                await th.send(embed=embed)
        except Exception as e:
            log.warning("Gagal tulis banlog: %s", e)

    @commands.command(name="_tb_secure_disabled", aliases=["testban"], help="Simulasi ban yang aman: reply pesan atau sebut member. Contoh: !tb [@user] [alasan]")
    @require_mod()
    @commands.guild_only()
    async def testban(self, ctx: commands.Context, member: Optional[discord.Member]=None, *, reason: str=""):
        if not self._guard(ctx.message.id):
            return
        target = await _resolve_target(ctx, member)
        if not isinstance(target, discord.Member):
            em = _embed_sim_fail(getattr(target, "mention", str(target)), "Target tidak ditemukan.", ctx.author)
            await ctx.reply(embed=em, mention_author=False)
            await self._log(ctx.guild, em)
            return
        try:
            em = _embed_sim_ok(target, ctx.author)
        except Exception:
            em = discord.Embed(
                title="💀 Simulasi Ban oleh SatpamBot",
                description=f"{getattr(target,'mention',str(target))} terdeteksi mengirim pesan mencurigakan.\n(Pesan ini hanya simulasi untuk pengujian.)",
                color=YEL,
            )
            em.set_footer(text=f"Moderator: {ctx.author}")
        await ctx.reply(embed=em, mention_author=False)
        await self._log(ctx.guild, em)

async def setup(bot: commands.Bot):
    # Jangan hapus command lain; cukup tambah cog ini
    await bot.add_cog(BanSecure(bot))
