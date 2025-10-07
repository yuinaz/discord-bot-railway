
from __future__ import annotations
import os, time, asyncio, math
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

from satpambot.config.runtime import cfg

HEAVY_COGS = [
  'anti_image_phash_runtime','anti_image_phash_runtime_strict','anti_image_phish_advanced',
  'anti_image_phish_guard','anti_image_scored_guard','imagephish_ref_indexer','live_metrics_push',
  'auto_repo_watcher','presence_mood_rotator','mood_watcher','slang_miner','learning_progress',
  'phash_auto_ban','phash_runtime_log_tamer','phish_hash_autoreseed','phish_hash_inbox',
]
NAP_SLEEP_EXTRA = ['chat_neurolite','slash_basic','slash_list_broadcast','name_wake_autoreply','name_wake_autoreply_enhanced','info','help_basic']

def _ext_path(name: str) -> str: return f'satpambot.bot.modules.discord_bot.cogs.{name}'
def is_owner(user: 'discord.abc.User') -> bool:
    owner_id = cfg('OWNER_USER_ID'); return bool(owner_id and str(user.id) == str(owner_id))
def _clamp(v: float, lo: float, hi: float) -> float: return max(lo, min(hi, v))

class SelfMaintenanceManager(commands.Cog):  # type: ignore
    def __init__(self, bot: 'commands.Bot'):
        self.bot = bot
        self.mode = 'full'
        self.auto_enabled = cfg('MAINTENANCE_AUTO', True)
        self.nap_enabled  = cfg('NAP_ENABLE', True)

        self.max_off = int(cfg('NAP_MAX_OFF')); self.min_off = int(cfg('NAP_MIN_OFF'))
        self.min_on  = int(cfg('NAP_MIN_ON'));  self.max_on  = int(cfg('NAP_MAX_ON'))
        self.cpu_lo  = float(cfg('NAP_CPU_LOW')); self.cpu_hi = float(cfg('NAP_CPU_HIGH'))
        self.msg_lo  = float(cfg('NAP_MSG_LOW')); self.msg_hi = float(cfg('NAP_MSG_HIGH'))
        self.alpha   = float(cfg('NAP_ADAPT_ALPHA'))

        # Noon relax config (WIB default UTC+7)
        self.relax_enable = bool(str(cfg('RELAX_NOON_ENABLE', 'true')).lower() in ('1','true','yes','on'))
        self.relax_start_hhmm = str(cfg('RELAX_NOON_START', '12:00'))
        self.relax_duration_min = int(cfg('RELAX_NOON_DURATION_MIN', 30))
        self.relax_tz_offset_min = int(cfg('RELAX_TZ_OFFSET_MIN', 420))  # +07:00

        self.unloaded: List[str] = []; self.nap_unloaded: List[str] = []
        self.nap_sleeping = False; self.msg_count_window = 0
        self.cpu_ema = None; self.msg_ema = None
        self._phase_end_ts = time.time() + 60
        self._on_min = self.min_on; self._off_min = self.min_off

        # quiet-now (forced nap) until timestamp
        self._quiet_until_ts = 0.0

        if hasattr(self,'auto_loop'): self.auto_loop.start()  # type: ignore
        if hasattr(self,'nap_loop'):  self.nap_loop.start()   # type: ignore
        if hasattr(self,'adapt_loop'): self.adapt_loop.start()# type: ignore

    def _mk_embed(self, title: str, desc: str, color: int):
        if discord is None: return None
        return discord.Embed(title=title, description=desc, color=color)

    def _cpu_usage(self) -> float:
        try:
            import psutil; return float(psutil.cpu_percent(interval=0.3))
        except Exception:
            try:
                la1, _, _ = os.getloadavg()
                import multiprocessing as mp
                cores = max(1, mp.cpu_count())
                return _clamp((la1 / cores) * 100.0, 0.0, 100.0)
            except Exception:
                return 0.0

    def _local_hhmm(self) -> int:
        # returns minutes since midnight at configured tz
        tz = self.relax_tz_offset_min
        t = time.time() + tz*60
        lt = time.gmtime(t)
        return lt.tm_hour*60 + lt.tm_min

    def _relax_now(self) -> bool:
        if not self.relax_enable: return False
        try:
            hh, mm = self.relax_start_hhmm.split(':')
            start_min = int(hh)*60 + int(mm)
        except Exception:
            start_min = 12*60
        cur = self._local_hhmm()
        return start_min <= cur < (start_min + max(1, self.relax_duration_min))

    async def _dm_owner(self, embed):
        if discord is None or embed is None or not cfg('NAP_DM_NOTIF', False): return
        owner_id = cfg('OWNER_USER_ID')
        if not owner_id: return
        try:
            user = self.bot.get_user(int(owner_id)) or await self.bot.fetch_user(int(owner_id))
            if user: await user.send(embed=embed)
        except Exception: pass

    async def set_half_power(self):
        if self.mode == 'half': return
        self.unloaded = []
        for name in HEAVY_COGS:
            ext = _ext_path(name)
            try:
                if ext in self.bot.extensions:
                    self.bot.unload_extension(ext); self.unloaded.append(ext)
            except Exception: pass
        self.mode = 'half'

    async def set_full_power(self):
        if self.mode == 'full': return
        for ext in list(self.unloaded):
            try: self.bot.load_extension(ext)
            except Exception: pass
        self.unloaded.clear()
        for ext in list(self.nap_unloaded):
            try: self.bot.load_extension(ext)
            except Exception: pass
        self.nap_unloaded.clear()
        self.mode = 'full'

    async def _nap_sleep(self):
        for name in NAP_SLEEP_EXTRA:
            ext = _ext_path(name)
            try:
                if ext in self.bot.extensions:
                    self.bot.unload_extension(ext)
                    if ext not in self.nap_unloaded: self.nap_unloaded.append(ext)
            except Exception: pass
        self.nap_sleeping = True; self.mode = 'nap'
        if discord:
            try: await self.bot.change_presence(status=discord.Status.idle, activity=discord.Game('napping…'))
            except Exception: pass
        await self._dm_owner(self._mk_embed('Nap', 'Entering sleep window (reduced activity).', 0x95a5a6))

    async def _nap_wake(self):
        for ext in list(self.nap_unloaded):
            try: self.bot.load_extension(ext)
            except Exception: pass
        self.nap_unloaded.clear(); self.nap_sleeping = False
        if self.mode == 'nap': self.mode = 'half'
        if discord:
            try: await self.bot.change_presence(status=discord.Status.online, activity=discord.Game('stretching…'))
            except Exception: pass
        await self._dm_owner(self._mk_embed('Nap', 'Waking to active window (half-power).', 0x2ecc71))

    def _activity_index(self) -> float:
        cpu = self._cpu_usage(); a = self.alpha
        self.cpu_ema = cpu if self.cpu_ema is None else (a*cpu + (1-a)*self.cpu_ema)
        mpmin = self.msg_count_window; self.msg_count_window = 0
        self.msg_ema = mpmin if self.msg_ema is None else (a*mpmin + (1-a)*self.msg_ema)
        def norm(x, lo, hi): return 0.0 if hi <= lo else _clamp((x-lo)/(hi-lo), 0.0, 1.0)
        return _clamp(0.6*norm(self.cpu_ema, float(self.cpu_lo), float(self.cpu_hi)) + 0.4*norm(self.msg_ema, float(self.msg_lo), float(self.msg_hi)), 0.0, 1.0)

    def _recompute_windows(self):
        # Respect forced quiet-now
        if time.time() < self._quiet_until_ts:
            self._off_min = int(math.ceil((self._quiet_until_ts - time.time())/60.0))
            self._on_min = self.min_on
            return

        idx = self._activity_index(); restful = 1.0 - idx
        off_target = int(round(_clamp(restful * int(self.max_off), int(self.min_off), int(self.max_off))))
        on_span = int(self.max_on) - int(self.min_on)
        on_target = int(round(_clamp(int(self.min_on) + (idx * on_span), int(self.min_on), int(self.max_on))))

        # Noon relax window: ensure minimum off duration
        if self._relax_now():
            off_target = max(off_target, min(self.relax_duration_min, int(self.max_off)))

        self._on_min = on_target; self._off_min = off_target

    @tasks.loop(seconds=60)
    async def adapt_loop(self):
        if not self.nap_enabled: return
        self._recompute_windows()

    @tasks.loop(seconds=10)
    async def nap_loop(self):
        if not self.nap_enabled: return
        now = time.time()
        if now >= self._phase_end_ts:
            if self.nap_sleeping:
                await self._nap_wake(); self._phase_end_ts = now + max(1, self._on_min) * 60
            else:
                await self._nap_sleep(); self._phase_end_ts = now + max(1, self._off_min) * 60

    @tasks.loop(seconds=60)
    async def auto_loop(self):
        if not self.auto_enabled: return
        cpu = self._cpu_usage()
        try:
            half = int(cfg('MAINT_HALF_CPU')); resume = int(cfg('MAINT_RESUME_CPU'))
        except Exception:
            half, resume = 85, 50
        if self.mode in ('full','nap') and cpu >= half:
            await self.set_half_power()
        elif self.mode == 'half' and cpu <= resume and not self.nap_sleeping:
            await self.set_full_power()

    @commands.Cog.listener()
    async def on_message(self, message: 'discord.Message'):
        if discord is None: return
        if not message.author.bot: self.msg_count_window += 1
        if not isinstance(message.channel, (discord.DMChannel, discord.GroupChannel)): return
        if not is_owner(message.author): return
        txt = message.content.strip().lower()
        if txt in ('power half','half power','1/2 power'):
            await self.set_half_power(); await message.channel.send(embed=self._mk_embed('Power', 'Switched to **HALF** power.', 0xf39c12))
        elif txt in ('power full','full power'):
            await self.set_full_power(); await message.channel.send(embed=self._mk_embed('Power', 'Switched to **FULL** power.', 0x2ecc71))
        elif txt in ('power status','status power'):
            mode = f"{self.mode} (sleeping)" if self.nap_sleeping else self.mode
            await message.channel.send(embed=self._mk_embed('Power Status', f'Mode: **{mode}**\nNap windows: ON {self._on_min}m / OFF {self._off_min}m', 0x3498db))
        elif txt.startswith('quiet now '):
            try:
                mins = int(txt.split('quiet now ',1)[1].strip())
                mins = int(_clamp(mins, 1, int(cfg('NAP_MAX_OFF',30))))
                self._quiet_until_ts = time.time() + mins*60
                self.nap_enabled = True
                await self._nap_sleep()
                self._phase_end_ts = self._quiet_until_ts
                await message.channel.send(embed=self._mk_embed('Quiet Now', f'Forcing nap for **{mins} min**.', 0x95a5a6))
            except Exception:
                await message.channel.send('Format: `quiet now <minutes>`')
        elif txt in ('nap on','power nap on'):
            self.nap_enabled = True; await message.channel.send(embed=self._mk_embed('Nap', 'Nap mode **ON** (adaptive).', 0x2ecc71))
        elif txt in ('nap off','power nap off'):
            self.nap_enabled = False; await self._nap_wake(); await message.channel.send(embed=self._mk_embed('Nap', 'Nap mode **OFF**.', 0xe74c3c))
        elif txt in ('nap status','nap'):
            mode = f"{self.mode} (sleeping)" if self.nap_sleeping else self.mode
            extra = ' (noon relax active)' if self._relax_now() else ''
            await message.channel.send(embed=self._mk_embed('Nap Status', f'Adaptive: **{"on" if self.nap_enabled else "off"}**{extra}\nWindows: ON {self._on_min}m / OFF {self._off_min}m', 0x3498db))

    if app_commands:
        async def _owner_gate(self, interaction: 'discord.Interaction') -> bool:
            if not is_owner(interaction.user):
                await interaction.response.send_message('Owner only.', ephemeral=True); return False
            return True

        @app_commands.command(name='nap_status', description='(Owner) Lihat status Nap adaptif')
        async def nap_status(self, interaction: 'discord.Interaction'):
            if not await self._owner_gate(interaction): return
            mode = f"{self.mode} (sleeping)" if self.nap_sleeping else self.mode
            extra = ' (noon relax active)' if self._relax_now() else ''
            await interaction.response.send_message(embed=self._mk_embed('Nap Status', f'Adaptive: **{"on" if self.nap_enabled else "off"}**{extra}\nWindows: ON {self._on_min}m / OFF {self._off_min}m', 0x3498db), ephemeral=True)

        @app_commands.command(name='quiet_now', description='(Owner) Force nap for N minutes')
        async def quiet_now(self, interaction: 'discord.Interaction', minutes: int):
            if not await self._owner_gate(interaction): return
            minutes = int(_clamp(minutes, 1, int(cfg('NAP_MAX_OFF',30))))
            self._quiet_until_ts = time.time() + minutes*60
            self.nap_enabled = True
            await self._nap_sleep()
            self._phase_end_ts = self._quiet_until_ts
            await interaction.response.send_message(embed=self._mk_embed('Quiet Now', f'Forcing nap for **{minutes} min**.', 0x95a5a6), ephemeral=True)

async def setup(bot):
    if discord is None or commands is object:
        return
    await bot.add_cog(SelfMaintenanceManager(bot))
