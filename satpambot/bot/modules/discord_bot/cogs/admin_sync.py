
import logging
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

log = logging.getLogger(__name__)

class AdminSync(commands.Cog):
    """Robust slash sync: auto/global/guild/all-guilds with copy_global_to."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="sync", description="Sinkronisasi slash: auto/global/guild/all-guilds.")
    @app_commands.describe(type="Tipe sync")
    @app_commands.choices(
        type=[
            app_commands.Choice(name="auto", value="auto"),
            app_commands.Choice(name="global", value="global"),
            app_commands.Choice(name="guild", value="guild"),
            app_commands.Choice(name="all-guilds", value="all-guilds"),
        ]
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def do_sync(self, inter: discord.Interaction, type: Optional[app_commands.Choice[str]] = None):
        sel = (type.value if isinstance(type, app_commands.Choice) else "auto")
        tree = self.bot.tree
        # Try to defer, but don't die if already acknowledged
        deferred = False
        try:
            await inter.response.defer(ephemeral=True, thinking=True)
            deferred = True
        except Exception as e:
            log.warning("[admin_sync] defer failed: %s", e)

        async def _send(msg: str):
            if deferred:
                await inter.followup.send(msg, ephemeral=True)
            else:
                try:
                    await inter.response.send_message(msg, ephemeral=True)
                except Exception:
                    await inter.followup.send(msg, ephemeral=True)

        if sel == "global":
            cmds = await tree.sync()
            await _send(f"Synced **{len(cmds)}** global command.")
            return

        if sel == "all-guilds":
            total = 0
            for g in list(self.bot.guilds):
                try:
                    tree.copy_global_to(guild=g)
                    cmds = await tree.sync(guild=g)
                    total += len(cmds)
                except Exception as e:
                    log.warning("[admin_sync] sync guild %s failed: %s", getattr(g, 'id', '?'), e)
            await _send(f"Synced global→guild untuk **{len(self.bot.guilds)}** guild. Total entries: {total}.")
            return

        # default: current guild (auto/guild)
        g = inter.guild
        if g is None:
            cmds = await tree.sync()
            await _send(f"(No guild) Synced **{len(cmds)}** global command.")
            return

        try:
            # auto: copy global into this guild, then sync
            tree.copy_global_to(guild=g)
        except Exception as e:
            log.warning("[admin_sync] copy_global_to failed: %s", e)

        cmds = await tree.sync(guild=g)
        label = "auto" if sel == "auto" else "guild"
        await _send(f"Synced **{len(cmds)}** command ke guild **{g.id}** ({label}).")

async def setup(bot: commands.Bot):
    await bot.add_cog(AdminSync(bot))
