from __future__ import annotations
import os, json, logging
import discord
from discord import app_commands
from discord.ext import commands, tasks
from satpambot.bot.modules.discord_bot.helpers.runtime_cfg import ConfigManager

log = logging.getLogger(__name__)

def _is_admin(member: discord.Member) -> bool:
    if member.guild_permissions.administrator:
        return True
    env_ids = os.getenv("ADMIN_USER_IDS")
    if env_ids:
        try:
            allow = {int(t) for t in env_ids.replace(" ", "").split(",") if t.isdigit()}
            if member.id in allow: return True
        except Exception:
            pass
    return False

class RuntimeCfgManager(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.cfg = ConfigManager.instance()
        self.watcher.start()

    def cog_unload(self):
        try: self.watcher.cancel()
        except Exception: pass

    @tasks.loop(seconds=45.0)
    async def watcher(self):
        self.cfg.maybe_reload()

    @watcher.before_loop
    async def before_watcher(self):
        await self.bot.wait_until_ready()

    group = app_commands.Group(name="cfg", description="Runtime config SatpamBot")

    @group.command(name="show", description="Lihat konfigurasi runtime")
    async def show(self, interaction: discord.Interaction):
        if not _is_admin(interaction.user):
            await interaction.response.send_message("Nope.", ephemeral=True); return
        data = self.cfg._data
        text = json.dumps(data, ensure_ascii=False, indent=2)[:1900]
        await interaction.response.send_message(f"```json\n{text}\n```", ephemeral=True)

    @group.command(name="set", description="Set key path (dot) ke value")
    @app_commands.describe(path="contoh: status_pin.interval_min", value="nilai")
    async def set(self, interaction: discord.Interaction, path: str, value: str):
        if not _is_admin(interaction.user):
            await interaction.response.send_message("Nope.", ephemeral=True); return
        v: object = value
        low = value.strip().lower()
        if low in ("true","false","1","0","on","off"):
            v = low in ("true","1","on")
        else:
            try:
                v = float(value) if "." in value else int(value)
            except Exception:
                pass
        self.cfg.set(path, v)
        await interaction.response.send_message(f"OK set `{path}` -> `{v}`", ephemeral=True)

    @group.command(name="reload", description="Reload config dari file")
    async def reload(self, interaction: discord.Interaction):
        if not _is_admin(interaction.user):
            await interaction.response.send_message("Nope.", ephemeral=True); return
        self.cfg.reload()
        await interaction.response.send_message("Reloaded.", ephemeral=True)

async def setup(bot: commands.Bot):
    cog = RuntimeCfgManager(bot)
    await bot.add_cog(cog)
    try: bot.tree.add_command(RuntimeCfgManager.group)
    except Exception: pass
