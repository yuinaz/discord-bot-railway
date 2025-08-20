import logging
from typing import Optional

import discord
from discord.ext import commands

from satpambot.bot.modules.discord_bot.utils.perm import require_mod
from satpambot.bot.modules.discord_bot.helpers.banlog_helper import get_banlog_thread

log = logging.getLogger(__name__)

GREEN = 0x3BA55D
RED   = 0xED4245

def _can_act(me: discord.Member, target: discord.Member) -> (bool, str):
    if target.id == me.id:
        return False, "Tidak bisa mem-ban diri sendiri."
    if target.guild.owner_id == target.id:
        return False, "Tidak bisa mem-ban **Owner** server."
    if me.top_role <= target.top_role and not me.guild_permissions.administrator:
        return False, "Role bot lebih rendah dari target."
    return True, ""

def _ban_embed(actor: discord.Member, target: discord.Member, reason: Optional[str], ok: bool) -> discord.Embed:
    e = discord.Embed(
        title="Ban Executed" if ok else "Ban Failed",
        color=GREEN if ok else RED,
    )
    e.add_field(name="Target", value=f"{target} (`{target.id}`)", inline=False)
    e.add_field(name="By", value=f"{actor} (`{actor.id}`)", inline=False)
    if reason: e.add_field(name="Reason", value=reason, inline=False)
    return e

class BanCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="ban")
    @require_mod()
    @commands.guild_only()
    async def ban(self, ctx: commands.Context, member: discord.Member, *, reason: Optional[str] = None):
        me = ctx.guild.me
        ok, why = _can_act(me, member)
        if not ok:
            await ctx.reply(f"❌ {why}", mention_author=False)
            # log fail
            th = await get_banlog_thread(ctx.guild)
            if th:
                await th.send(embed=_ban_embed(ctx.author, member, why, ok=False))
            return
        try:
            await ctx.guild.ban(member, reason=reason or f"By {ctx.author} via command", delete_message_days=0)
            await ctx.reply(f"✅ **{member}** diban. {('Alasan: '+reason) if reason else ''}", mention_author=False)
            # log success
            th = await get_banlog_thread(ctx.guild)
            if th:
                await th.send(embed=_ban_embed(ctx.author, member, reason, ok=True))
        except discord.Forbidden:
            msg = "Gagal ban: bot tidak punya izin yang cukup."
            await ctx.reply(f"❌ {msg}", mention_author=False)
            th = await get_banlog_thread(ctx.guild)
            if th:
                await th.send(embed=_ban_embed(ctx.author, member, msg, ok=False))
        except discord.HTTPException as e:
            msg = f"Gagal ban: {e}"
            await ctx.reply(f"❌ {msg}", mention_author=False)
            th = await get_banlog_thread(ctx.guild)
            if th:
                await th.send(embed=_ban_embed(ctx.author, member, msg, ok=False))

    @commands.command(name="tb_raw", aliases=["testban_raw"])
    @require_mod()
    @commands.guild_only()
    async def testban(self, ctx: commands.Context, member: discord.Member):
        me = ctx.guild.me
        ok, why = _can_act(me, member)
        if not ok:
            return await ctx.reply(f"⚠️ Tidak bisa ban: {why}", mention_author=False)
        if not (me.guild_permissions.ban_members or me.guild_permissions.administrator):
            return await ctx.reply("⚠️ Bot tidak punya izin ban_members/administrator.", mention_author=False)
        await ctx.reply(f"🧪 OK. Bot **dapat** memban **{member}** (simulasi).", mention_author=False)

async def setup(bot: commands.Bot):
    # Remove old commands if present to avoid duplicates
    for name in ("ban","tb","testban"):
        try:
            cmd = bot.get_command(name)
            if cmd:
                bot.remove_command(name)
        except Exception:
            pass
    await bot.add_cog(BanCommands(bot))