
from __future__ import annotations
import os, traceback
import discord
from discord.ext import commands

def _resolve_error_channel(bot: commands.Bot, guild: discord.Guild | None) -> discord.TextChannel | None:
    raw = os.getenv("ERROR_LOG_CHANNEL_ID") or os.getenv("LOG_CHANNEL_ID") or ""
    if raw.isdigit():
        ch = bot.get_channel(int(raw))
        if isinstance(ch, discord.TextChannel):
            return ch
    if guild:
        for ch in guild.text_channels:
            if ch.permissions_for(guild.me).send_messages:
                return ch
    return None

class ErrorLogBridge(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if getattr(error, "handled", False):
            return
        ch = _resolve_error_channel(self.bot, getattr(ctx, "guild", None))
        if not ch: return
        tb = "".join(traceback.format_exception(type(error), error, error.__traceback__))
        msg = f"❌ **Command error** in `{ctx.command}` by {ctx.author.mention}\n```py\n{tb[-1800:]}\n```"
        try:
            await ch.send(msg)
        except Exception:
            pass

    @commands.Cog.listener()
    async def on_error(self, event_method: str, *args, **kwargs):
        ch = None
        try:
            guild = None
            for arg in args:
                if hasattr(arg, "guild"):
                    guild = arg.guild
                    break
            ch = _resolve_error_channel(self.bot, guild)
            if not ch: return
            tb = traceback.format_exc()
            if not tb or tb == "NoneType: None\n": return
            msg = f"⚠️ **Event error in** `{event_method}`\n```py\n{tb[-1800:]}\n```"
            await ch.send(msg)
        except Exception:
            pass

    @commands.command(name="errorlog-ping")
    @commands.has_permissions(administrator=True)
    async def errorlog_ping(self, ctx: commands.Context):
        ch = _resolve_error_channel(self.bot, ctx.guild)
        await ctx.reply(f"Errorlog channel: {ch.mention if ch else '(none)'}")

async def setup(bot: commands.Bot):
    await bot.add_cog(ErrorLogBridge(bot))
