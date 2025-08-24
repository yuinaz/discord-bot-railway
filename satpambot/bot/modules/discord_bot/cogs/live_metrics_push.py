
import os, json, time, asyncio
from pathlib import Path
from datetime import datetime, timezone
from discord.ext import commands, tasks

try:
    import psutil
except Exception:
    psutil = None

METRICS_FILE = os.getenv("METRICS_FILE", "data/live_metrics.json")
PUSH_INTERVAL = int(os.getenv("METRICS_PUSH_INTERVAL", "30"))

class LiveMetricsPush(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.start_ts = time.time()
        self.push_loop.change_interval(seconds=max(5, PUSH_INTERVAL))
        self.push_loop.start()

    def cog_unload(self):
        self.push_loop.cancel()

    @commands.Cog.listener()
    async def on_ready(self):
        for g in list(self.bot.guilds):
            try:
                await g.chunk(cache=True)
            except Exception:
                pass
        await self._write_metrics()

    async def _collect_async(self) -> dict:
        guilds = list(self.bot.guilds)
        guild_count = len(guilds)

        total_members = 0
        online = 0
        channels = 0
        threads = 0

        for g in guilds:
            try:
                channels += len(getattr(g, "channels", []) or [])
            except Exception:
                pass
            try:
                threads += len(getattr(g, "threads", []) or [])
            except Exception:
                pass
            try:
                if g.member_count is not None:
                    total_members += int(g.member_count)
            except Exception:
                pass
            try:
                for m in getattr(g, "members", []) or []:
                    s = str(getattr(m, "status", "offline"))
                    if s != "offline":
                        online += 1
            except Exception:
                pass

        if total_members == 0 and guilds:
            try:
                from discord.http import Route
                approx_sum = 0
                for g in guilds:
                    route = Route("GET", "/guilds/{guild_id}", guild_id=g.id)
                    data = await self.bot.http.request(route, params={"with_counts": True})
                    approx_sum += int(data.get("approximate_member_count", 0))
                total_members = approx_sum
            except Exception:
                pass

        latency_ms = int((self.bot.latency or 0.0) * 1000)
        cpu = 0.0
        ram_mb = 0
        mem_pct = None
        if psutil:
            try:
                vm = psutil.virtual_memory()
                cpu = float(psutil.cpu_percent(interval=None))
                ram_mb = int(vm.used / 1024 / 1024)
                mem_pct = float(vm.percent)
            except Exception:
                pass

        return {
            "ok": True,
            "updated_at": datetime.utcnow().replace(tzinfo=timezone.utc).isoformat(),
            "guilds": guild_count,
            "members": total_members,
            "members_online": online,
            "channels": channels,
            "threads": threads,
            "latency_ms": latency_ms,
            "cpu_percent": cpu,
            "ram_mb": ram_mb,
            "uptime_s": round(time.time() - self.start_ts, 1),
            
# compatibility & richer keys for dashboard
"online": online,
"cpu_pct": round(cpu, 1) if cpu is not None else None,
"ram_pct": round(mem_pct, 1) if mem_pct is not None else None,
"uptime": int(time.time() - self.start_ts),

        }

    def _write_file(self, payload: dict):
        try:
            p = Path(METRICS_FILE)
            p.parent.mkdir(parents=True, exist_ok=True)
            tmp = p.with_suffix(p.suffix + ".tmp")
            tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp.replace(p)
        except Exception as e:
            print(f"[metrics] write error: {e}")

    @tasks.loop(seconds=500)
    async def push_loop(self):
        await self._write_metrics()

    @push_loop.before_loop
    async def _before(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(3)

    async def _write_metrics(self):
        data = await self._collect_async()
        try:
            from satpambot.dashboard import live_store as _ls  # type: ignore
            _ls.STATS = {**data, "ts": int(time.time())}
        except Exception as e:
            print(f"[metrics] live_store error: {e}")
        self._write_file({**data, "ts": int(time.time())})

async def setup(bot):
    await bot.add_cog(LiveMetricsPush(bot))
