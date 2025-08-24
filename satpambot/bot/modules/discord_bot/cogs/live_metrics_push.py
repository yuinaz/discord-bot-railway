
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


# === sticky embed helpers (free plan friendly) ===
import json, time
from pathlib import Path
from datetime import datetime, timedelta, timezone
try:
    from zoneinfo import ZoneInfo as _Zone
except Exception:
    _Zone = None

def _tz_wib():
    try:
        return _Zone("Asia/Jakarta")
    except Exception:
        return timezone(timedelta(hours=7))

def _sticky_store_path():
    root = os.getenv("STICKY_MESSAGE_FILE", "data/sticky_embed.json")
    p = Path(root)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p

def _sticky_load():
    p = _sticky_store_path()
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}

def _sticky_save(d:dict):
    p = _sticky_store_path()
    try:
        p.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass


async def _sticky_poster(self):
    # post/update sticky embed periodically using collected metrics
    chan_id = int(os.getenv("STICKY_CHANNEL_ID", "0") or 0)
    if not chan_id:
        return
    last_hash = None
    last_edit = 0
    force_every = int(os.getenv("STICKY_FORCE_SEC", "60"))
    while True:
        try:
            ch = self.bot.get_channel(chan_id) or await self.bot.fetch_channel(chan_id)
            payload = await self._collect_async()
            # Build embed text (simple text to avoid heavy styling on free plan)
            online = payload.get("online") or payload.get("members_online") or 0
            cpu = payload.get("cpu_pct") or payload.get("cpu_percent") or 0
            ram = payload.get("ram_pct") or payload.get("ram_mb") or 0
            ts = datetime.now(_tz_wib())
            content = f"LeinDiscord • online={online} • CPU={cpu}% • RAM={ram}% • {ts:%Y-%m-%d %H:%M:%S} WIB"
            # locate sticky message id from store
            store = _sticky_load()
            key = str(chan_id)
            msg_id = store.get(key)
            msg = None
            if msg_id:
                try:
                    msg = await ch.fetch_message(int(msg_id))
                except Exception:
                    msg = None
            if not msg:
                m = await ch.send(content)
                store[key] = str(m.id)
                _sticky_save(store)
                last_hash = None
            else:
                # Only edit if changed or forced by time
                h = hash(content)
                now = time.time()
                if h != last_hash or (now - last_edit) >= force_every:
                    await msg.edit(content=content)
                    last_hash = h
                    last_edit = now
        except Exception:
            pass
        await asyncio.sleep(float(os.getenv("STICKY_UPDATE_SEC", "15")))
