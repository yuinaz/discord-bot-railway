import logging
from typing import Optional

import discord
from discord.ext import commands

from satpambot.bot.modules.discord_bot.utils.perm import require_mod

log = logging.getLogger(__name__)

def _can_act(me: discord.Member, target: discord.Member) -> (bool, str):
    if target.id == me.id:
        return False, "Tidak bisa mem-ban diri sendiri."
    if target.guild.owner_id == target.id:
        return False, "Tidak bisa mem-ban **Owner** server."
    if me.top_role <= target.top_role and not me.guild_permissions.administrator:
        return False, "Role bot lebih rendah dari target."
    return True, ""

class BanOverrides(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="ban")
    @require_mod()
    @commands.guild_only()
    async def ban(self, ctx: commands.Context, member: discord.Member, *, reason: Optional[str] = None):
        """Ban member. Contoh: !ban @user [alasan]"""
        me = ctx.guild.me
        ok, why = _can_act(me, member)
        if not ok:
            return await ctx.reply(f"❌ {why}", mention_author=False)
        try:
            await ctx.guild.ban(member, reason=reason or f"By {ctx.author} via command", delete_message_days=0)
            await ctx.reply(f"✅ **{member}** diban. {('Alasan: '+reason) if reason else ''}", mention_author=False)
        except discord.Forbidden:
            await ctx.reply("❌ Gagal ban: bot tidak punya izin yang cukup.", mention_author=False)
        except discord.HTTPException as e:
            await ctx.reply(f"❌ Gagal ban: {e}", mention_author=False)

    @commands.command(name="tb", aliases=["testban"])
    @require_mod()
    @commands.guild_only()
    async def testban(self, ctx: commands.Context, member: discord.Member):
        """Cek apakah bot **bisa** memban target (dry-run)."""
        me = ctx.guild.me
        ok, why = _can_act(me, member)
        if not ok:
            return await ctx.reply(f"⚠️ Tidak bisa ban: {why}", mention_author=False)
        if not (me.guild_permissions.ban_members or me.guild_permissions.administrator):
            return await ctx.reply("⚠️ Bot tidak punya izin ban_members/administrator.", mention_author=False)
        await ctx.reply(f"🧪 OK. Bot **dapat** memban **{member}** (simulasi, tidak diban).", mention_author=False)

async def setup(bot: commands.Bot):
    # Remove existing commands if already registered to prevent conflicts
    for name in ("ban","tb","testban"):
        try:
            cmd = bot.get_command(name)
            if cmd:
                bot.remove_command(name)
        except Exception:
            pass
    await bot.add_cog(BanOverrides(bot))