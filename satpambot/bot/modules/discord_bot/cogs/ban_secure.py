from __future__ import annotations
import logging, asyncio
from typing import Optional
import discord
from discord.ext import commands
from satpambot.bot.modules.discord_bot.utils.perm import require_mod
from satpambot.bot.modules.discord_bot.helpers.banlog_helper import get_banlog_thread

log = logging.getLogger(__name__)
GREEN = 0x3BA55D
RED   = 0xED4245
YEL   = 0xFEE75C

def _embed(title: str, desc: str, ok: bool|None=None) -> discord.Embed:
    color = GREEN if ok is True else RED if ok is False else YEL
    return discord.Embed(title=title, description=desc, color=color)

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
        """Simulasi ban: cek apakah BOT **bisa** memban target (tanpa eksekusi)."""
        if not isinstance(member, discord.Member):
            return await ctx.reply("Format: `!tb @user [alasan]`", mention_author=False)
        me = ctx.guild.me
        ok, why = _can_act(me, member)
        if not ok:
            await ctx.reply(f"❌ Tidak bisa ban **{member}**: {why}", mention_author=False)
            await self._log(ctx.guild, _embed("TEST BAN GAGAL", f"Mod: {ctx.author.mention}\nTarget: {member.mention}\nAlasan: {reason or '-'}\nDetail: {why}", ok=False))
            return
        await ctx.reply(f"🧪 OK. Bot **DAPAT** memban **{member}** (simulasi).", mention_author=False)
        await self._log(ctx.guild, _embed("TEST BAN OK", f"Mod: {ctx.author.mention}\nTarget: {member.mention}\nAlasan: {reason or '-'}", ok=True))

    @commands.command(name="ban")
    @require_mod()
    @commands.guild_only()
    @commands.has_guild_permissions(ban_members=True)
    async def ban(self, ctx: commands.Context, member: Optional[discord.Member]=None, *, reason: str=""):
        """Ban member dan catat ke banlog thread."""
        if not isinstance(member, discord.Member):
            return await ctx.reply("Format: `!ban @user [alasan]`", mention_author=False)
        me = ctx.guild.me
        ok, why = _can_act(me, member)
        if not ok:
            await ctx.reply(f"❌ Tidak bisa ban **{member}**: {why}", mention_author=False)
            await self._log(ctx.guild, _embed("BAN GAGAL", f"Mod: {ctx.author.mention}\nTarget: {member.mention}\nAlasan: {reason or '-'}\nDetail: {why}", ok=False))
            return
        try:
            await member.ban(reason=reason or f"Moderator: {ctx.author}")
            await ctx.reply(f"✅ Dibanned: **{member}**", mention_author=False)
            await self._log(ctx.guild, _embed("BANNED", f"Mod: {ctx.author.mention}\nTarget: {member.mention}\nAlasan: {reason or '-'}", ok=True))
        except discord.Forbidden:
            await ctx.reply("❌ Gagal ban: Forbidden (izin bot kurang).", mention_author=False)
            await self._log(ctx.guild, _embed("BAN GAGAL", f"Mod: {ctx.author.mention}\nTarget: {member.mention}\nDetail: Forbidden", ok=False))
        except discord.HTTPException as e:
            await ctx.reply(f"❌ Gagal ban: {e}", mention_author=False)
            await self._log(ctx.guild, _embed("BAN GAGAL", f"Mod: {ctx.author.mention}\nTarget: {member.mention}\nDetail: {e}", ok=False))

async def setup(bot: commands.Bot):
    # if old commands exist, remove them to avoid conflicts
    for name in ("ban","tb","testban"):
        try:
            cmd = bot.get_command(name)
            if cmd:
                bot.remove_command(name)
        except Exception:
            pass
    await bot.add_cog(BanSecure(bot))
