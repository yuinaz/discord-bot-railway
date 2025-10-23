from __future__ import annotations

from discord.ext import commands

import logging

import discord
from discord import app_commands

LOGGER = logging.getLogger(__name__)

DEFAULT_LIMIT = 100  # can edit in-file

class ClearChatForce(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="clearchat")
    @commands.has_permissions(manage_messages=True)
    async def clearchat_cmd(self, ctx: commands.Context, limit: int = DEFAULT_LIMIT):
        try:
            await ctx.message.delete()
        except Exception:
            pass
        try:
            await ctx.channel.purge(limit=limit)
        except Exception as e:
            LOGGER.exception("clearchat purge failed: %s", e)

    @app_commands.command(name="clearchat", description="Delete recent messages immediately.")
    @app_commands.describe(limit="How many messages to delete (default 100)")
    async def clearchat_slash(self, interaction: discord.Interaction, limit: int = DEFAULT_LIMIT):
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("No permission.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True, thinking=False)
        try:
            channel = interaction.channel
            if isinstance(channel, (discord.TextChannel, discord.Thread)):
                await channel.purge(limit=limit)
                await interaction.followup.send(f"Deleted {{limit}} messages.", ephemeral=True)
        except Exception as e:
            LOGGER.exception("clearchat slash purge failed: %s", e)
async def setup(bot: commands.Bot):
    await bot.add_cog(ClearChatForce(bot))