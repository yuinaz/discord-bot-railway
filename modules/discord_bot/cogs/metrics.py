import discord
from discord.ext import commands, tasks
import asyncio
from modules.discord_bot.helpers.metrics_agg import inc, snapshot, LATEST_METRICS
from modules.discord_bot.helpers.sheets_webhook import (
    log_command, log_moderation_ban, log_moderation_unban, log_system_metrics
)

class MetricsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.push_metrics.start()  # background task

    def cog_unload(self):
        self.push_metrics.cancel()

    @commands.Cog.listener()
    async def on_command(self, ctx: commands.Context):
        inc("commands_total")

    @commands.Cog.listener()
    async def on_command_completion(self, ctx: commands.Context):
        inc("commands_ok")
        try:
            await log_command(
                ctx.guild.id if ctx.guild else "",
                ctx.author.id if ctx.author else "",
                ctx.command.qualified_name if ctx.command else "",
                "ok"
            )
        except Exception:
            pass

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error):
        inc("commands_err")
        try:
            await log_command(
                ctx.guild.id if ctx.guild else "",
                ctx.author.id if ctx.author else "",
                ctx.command.qualified_name if ctx.command else "",
                "error"
            )
        except Exception:
            pass

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        inc("moderation.ban")
        try:
            await log_moderation_ban(guild.id, user.id)
        except Exception:
            pass

    @commands.Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, user: discord.User):
        inc("moderation.unban")
        try:
            await log_moderation_unban(guild.id, user.id)
        except Exception:
            pass

    @tasks.loop(seconds=60.0)
    async def push_metrics(self):
        # periodically send system metrics to sheets (optional)
        try:
            gid = self.bot.guilds[0].id if self.bot.guilds else ""
            await log_system_metrics(gid, LATEST_METRICS)
        except Exception:
            pass

async def setup(bot: commands.Bot):
    await bot.add_cog(MetricsCog(bot))
