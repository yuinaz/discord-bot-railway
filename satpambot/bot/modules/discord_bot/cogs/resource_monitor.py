
from __future__ import annotations
import os, time, shutil
import platform
try:
    import psutil
except Exception:
    psutil = None  # type: ignore

import discord
from discord.ext import commands, tasks
from satpambot.config.runtime import cfg

def _mk_embed(title: str, desc: str, color: int):
    return discord.Embed(title=title, description=desc, color=color)

def _percent_bar(pct: float, width: int = 16) -> str:
    pct = max(0.0, min(100.0, pct))
    filled = int(round((pct/100.0)*width))
    return '█'*filled + '░'*(width-filled)

def _status_channel(bot: commands.Bot):
    cid = cfg('STATUS_CHANNEL_ID')
    try:
        if cid:
            ch = bot.get_channel(int(cid))
            return ch
    except Exception:
        return None
    return None

class ResourceMonitor(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.interval = int(cfg('RESMON_INTERVAL_SEC', 300))
        self.cpu_warn = float(cfg('RESMON_CPU_WARN', 85))
        self.mem_warn = float(cfg('RESMON_MEM_WARN', 85))
        self.disk_warn = float(cfg('RESMON_DISK_WARN', 90))
        self.cooldown = int(cfg('RESMON_COOLDOWN_SEC', 1800))  # 30 min
        self._last_alert = 0.0
        if hasattr(self, 'loop'):
            self.loop.change_interval(seconds=max(60, self.interval))  # type: ignore
            self.loop.start()  # type: ignore

    def _snapshot(self):
        # CPU
        if psutil:
            cpu = float(psutil.cpu_percent(interval=0.2))
            vm = psutil.virtual_memory()
            mem_pct = float(vm.percent)
            rss_mb = float(psutil.Process().memory_info().rss) / (1024*1024)
        else:
            cpu = 0.0; mem_pct = 0.0; rss_mb = 0.0
        # Disk
        total, used, free = shutil.disk_usage('/')
        disk_pct = (used/total)*100.0 if total else 0.0
        # Uptime (process)
        try:
            if psutil:
                create = psutil.Process().create_time()
            else:
                create = time.time() - 0.0
        except Exception:
            create = time.time()
        uptime_min = (time.time() - create)/60.0
        return cpu, mem_pct, rss_mb, disk_pct, uptime_min

    def _make_embed(self, title='System Status'):
        cpu, mem_pct, rss_mb, disk_pct, uptime_min = self._snapshot()
        em = _mk_embed(title, f'Host: `{platform.node()}`', 0x3498db)
        em.add_field(name='CPU', value=f'{cpu:.1f}%\n{_percent_bar(cpu)}', inline=True)
        em.add_field(name='Memory', value=f'{mem_pct:.1f}% (RSS {rss_mb:.0f} MB)\n{_percent_bar(mem_pct)}', inline=True)
        em.add_field(name='Disk /', value=f'{disk_pct:.1f}%\n{_percent_bar(disk_pct)}', inline=True)
        em.add_field(name='Uptime', value=f'{uptime_min/60.0:.1f} h', inline=True)
        return em, cpu, mem_pct, disk_pct

    @tasks.loop(seconds=300)
    async def loop(self):
        try:
            em, cpu, mem_pct, disk_pct = self._make_embed('Periodic Status')
            alert = (cpu >= self.cpu_warn) or (mem_pct >= self.mem_warn) or (disk_pct >= self.disk_warn)
            now = time.time()
            if alert and (now - self._last_alert >= self.cooldown):
                self._last_alert = now
                owner = cfg('OWNER_USER_ID')
                if owner:
                    user = self.bot.get_user(int(owner)) or await self.bot.fetch_user(int(owner))
                    if user:
                        await user.send(embed=em)
                ch = _status_channel(self.bot)
                if ch:
                    try: await ch.send(embed=em)
                    except Exception: pass
        except Exception:
            pass

    @commands.Cog.listener()
    async def on_message(self, message: 'discord.Message'):
        if message.author.bot: return
        if not isinstance(message.channel, (discord.DMChannel, discord.GroupChannel)): return
        if str(message.content).strip().lower() in ('status now','report now'):
            em, *_ = self._make_embed('Status Now')
            await message.channel.send(embed=em)

    @discord.app_commands.command(name='status_now', description='Tampilkan status CPU/Mem/Disk saat ini')
    async def status_now(self, interaction: 'discord.Interaction'):
        em, *_ = self._make_embed('Status Now')
        await interaction.response.send_message(embed=em, ephemeral=True)

async def setup(bot):
    await bot.add_cog(ResourceMonitor(bot))
