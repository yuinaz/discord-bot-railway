from __future__ import annotations
import os, asyncio
from typing import List
try:
    import discord
    from discord import app_commands
    from discord.ext import commands, tasks
except Exception:
    discord = None  # type: ignore
    app_commands = None  # type: ignore
    commands = object  # type: ignore
    tasks = object  # type: ignore

HEAVY_COGS = [
  'anti_image_phash_runtime',
  'anti_image_phash_runtime_strict',
  'anti_image_phish_advanced',
  'anti_image_phish_guard',
  'anti_image_scored_guard',
  'imagephish_ref_indexer',
  'live_metrics_push',
  'auto_repo_watcher',
  'presence_mood_rotator',
  'mood_watcher',
  'slang_miner',
  'learning_progress',
  'phash_auto_ban',
  'phash_runtime_log_tamer',
  'phish_hash_autoreseed',
  'phish_hash_inbox',
]

def _ext_path(name: str) -> str:
    return f'satpambot.bot.modules.discord_bot.cogs.{name}'

def _is_owner_only() -> bool:
    return os.environ.get('COMMANDS_OWNER_ONLY','1') in ('1','true','on','yes')

def is_owner(user: 'discord.abc.User') -> bool:
    owner_id = os.environ.get('OWNER_USER_ID')
    if owner_id and str(user.id) == str(owner_id):
        return True
    return False if _is_owner_only() else False

class SelfMaintenanceManager(commands.Cog):  # type: ignore
    def __init__(self, bot: 'commands.Bot'):
        self.bot = bot
        self.mode = 'full'  # 'full' or 'half'
        self.auto_enabled = os.environ.get('MAINTENANCE_AUTO','1') not in ('0','false','off','no')
        self.unloaded: List[str] = []
        if hasattr(self,'auto_loop'):
            self.auto_loop.start()  # type: ignore

    def _mk_embed(self, title: str, desc: str, color: int):
        if discord is None:
            return None
        return discord.Embed(title=title, description=desc, color=color)

    async def set_half_power(self):
        if self.mode == 'half':
            return
        self.unloaded = []
        for name in HEAVY_COGS:
            ext = _ext_path(name)
            try:
                if ext in self.bot.extensions:
                    self.bot.unload_extension(ext)
                    self.unloaded.append(ext)
            except Exception:
                pass
        self.mode = 'half'

    async def set_full_power(self):
        if self.mode == 'full':
            return
        for ext in list(self.unloaded):
            try:
                self.bot.load_extension(ext)
            except Exception:
                pass
        self.unloaded.clear()
        self.mode = 'full'

    def _cpu_usage(self) -> float:
        try:
            import psutil
            return float(psutil.cpu_percent(interval=0.5))
        except Exception:
            try:
                la1, la5, la15 = os.getloadavg()
                import multiprocessing as mp
                cores = max(1, mp.cpu_count())
                return min(100.0, (la1 / cores) * 100)
            except Exception:
                return 0.0

    @tasks.loop(seconds=60)
    async def auto_loop(self):
        if not self.auto_enabled:
            return
        cpu = self._cpu_usage()
        try:
            half = int(os.environ.get('MAINT_HALF_CPU','85'))
            resume = int(os.environ.get('MAINT_RESUME_CPU','50'))
        except Exception:
            half, resume = 85, 50
        if self.mode == 'full' and cpu >= half:
            await self.set_half_power()
        elif self.mode == 'half' and cpu <= resume:
            await self.set_full_power()

    @commands.Cog.listener()
    async def on_message(self, message: 'discord.Message'):
        if discord is None or message.author.bot:
            return
        if not isinstance(message.channel, (discord.DMChannel, discord.GroupChannel)):
            return
        if not is_owner(message.author):
            return
        content = message.content.strip().lower()
        if content in ('power half','half power','1/2 power'):
            await self.set_half_power()
            await message.channel.send(embed=self._mk_embed('Power', 'Switched to **HALF** power.', 0xf39c12))
        elif content in ('power full','full power'):
            await self.set_full_power()
            await message.channel.send(embed=self._mk_embed('Power', 'Switched to **FULL** power.', 0x2ecc71))
        elif content in ('power status','status power'):
            await message.channel.send(embed=self._mk_embed('Power Status', f'Mode: **{self.mode}**\nUnloaded: {len(self.unloaded)}', 0x3498db))
        elif content in ('power auto on','auto power on'):
            self.auto_enabled = True
            await message.channel.send(embed=self._mk_embed('Power Auto', 'Auto maintenance **ON**.', 0x2ecc71))
        elif content in ('power auto off','auto power off'):
            self.auto_enabled = False
            await message.channel.send(embed=self._mk_embed('Power Auto', 'Auto maintenance **OFF**.', 0xe74c3c))

    if app_commands:
        async def _owner_gate(self, interaction: 'discord.Interaction') -> bool:
            owner_id = os.environ.get('OWNER_USER_ID')
            if owner_id and str(interaction.user.id) == str(owner_id):
                return True
            await interaction.response.send_message('Owner only.', ephemeral=True)
            return False

        @app_commands.command(name='power_half', description='(Owner) Switch to HALF power.')
        async def power_half(self, interaction: 'discord.Interaction'):
            if not await self._owner_gate(interaction): return
            await self.set_half_power()
            await interaction.response.send_message(embed=self._mk_embed('Power', 'Switched to **HALF** power.', 0xf39c12), ephemeral=True)

        @app_commands.command(name='power_full', description='(Owner) Switch to FULL power.')
        async def power_full(self, interaction: 'discord.Interaction'):
            if not await self._owner_gate(interaction): return
            await self.set_full_power()
            await interaction.response.send_message(embed=self._mk_embed('Power', 'Switched to **FULL** power.', 0x2ecc71), ephemeral=True)

        @app_commands.command(name='power_status', description='(Owner) Show current power mode.')
        async def power_status(self, interaction: 'discord.Interaction'):
            if not await self._owner_gate(interaction): return
            await interaction.response.send_message(embed=self._mk_embed('Power Status', f'Mode: **{self.mode}**', 0x3498db), ephemeral=True)

async def setup(bot):
    if discord is None or commands is object:
        return
    await bot.add_cog(SelfMaintenanceManager(bot))
