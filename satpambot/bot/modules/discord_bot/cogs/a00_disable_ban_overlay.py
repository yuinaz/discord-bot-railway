# satpambot/bot/modules/discord_bot/cogs/a00_disable_ban_overlay.py
from __future__ import annotations
import logging
from discord.ext import commands
try:
    from discord import app_commands
except Exception:
    app_commands = None

log = logging.getLogger(__name__)
DISABLED = {"ban","tban","tempban","unban"}

class DisableBanOverlay(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _remove_text(self):
        # Prefix/text commands
        for name in list(DISABLED):
            try:
                if self.bot.get_command(name):
                    self.bot.remove_command(name)
                    log.info("[ban-offloader] removed text command: %s", name)
            except Exception as e:
                log.debug("[ban-offloader] remove text %s failed: %r", name, e)

    async def _remove_slash(self):
        if not app_commands:
            return
        try:
            removed = 0
            # Iterate through top-level slash commands
            for cmd in list(self.bot.tree.get_commands() or []):
                try:
                    if cmd.name in DISABLED:
                        self.bot.tree.remove_command(cmd.name, type=None)
                        removed += 1
                        log.info("[ban-offloader] removed slash command: /%s", cmd.name)
                except Exception:
                    pass
            if removed:
                # sync silently; if fails, we still blocked by text removal
                try:
                    await self.bot.tree.sync()
                except Exception:
                    pass
        except Exception as e:
            log.debug("[ban-offloader] slash scan failed: %r", e)

    @commands.Cog.listener()
    async def on_ready(self):
        try:
            await self._remove_text()
        except Exception: pass
        try:
            await self._remove_slash()
        except Exception: pass
        log.info("[ban-offloader] ban/tban/tempban/unban disabled")

    @commands.Cog.listener()
    async def on_command(self, ctx: commands.Context):
        # Safety net: if somehow registered, block execution
        if ctx.command and ctx.command.name in DISABLED:
            await ctx.reply("❌ Fitur ban di Leina dimatikan. Gunakan **Nixe** untuk ban/unban.", mention_author=False)
            ctx.command.reset_cooldown(ctx)  # avoid cooldown effect
            raise commands.CheckFailure("ban disabled")

async def setup(bot: commands.Bot):
    await bot.add_cog(DisableBanOverlay(bot))
