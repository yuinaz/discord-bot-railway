
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

# Optional: push to dashboard over HTTP (Render-friendly if bot and web are separate services)
PUSH_URL = os.getenv("METRICS_PUSH_URL") or os.getenv("METRICS_INGEST_URL")  # e.g. https://your-app.onrender.com/api/metrics-ingest
PUSH_TOKEN = os.getenv("METRICS_INGEST_TOKEN", "")  # set same on web service to authorize

class LiveMetricsPush(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._last_payload = {}
        # start the loop a little after ready
        self.push_loop.start()

    def cog_unload(self):
        try:
            self.push_loop.cancel()
        except Exception:
            pass

    # ---- payload builder ----
    def _build_payload(self) -> dict:
        bot = self.bot
        try:
            guilds = len(getattr(bot, "guilds", []) or [])
        except Exception:
            guilds = 0

        members = 0
        online = 0
        channels = 0
        threads = 0
        try:
            for g in getattr(bot, "guilds", []) or []:
                try:
                    members += getattr(g, "member_count", 0) or 0
                except Exception:
                    pass
                try:
                    channels += len(getattr(g, "channels", []) or [])
                except Exception:
                    pass
                try:
                    threads += len(getattr(g, "threads", []) or [])
                except Exception:
                    pass
                try:
                    # online requires presence intent to be accurate; fallback to >0 status members
                    if getattr(g, "members", None):
                        online += sum(1 for m in g.members if getattr(getattr(m, "status", None), "value", str(getattr(m, "status", ""))) not in (None, "", "offline"))
                except Exception:
                    pass
        except Exception:
            pass

        try:
            latency_ms = int(round((getattr(bot, "latency", 0.0) or 0.0) * 1000))
        except Exception:
            latency_ms = 0

        cpu_percent = 0.0
        ram_mb = 0
        if psutil is not None:
            try:
                cpu_percent = float(psutil.cpu_percent(interval=None) or 0.0)
            except Exception:
                pass
            try:
                ram_mb = int((psutil.virtual_memory().used or 0) / 1024 / 1024)
            except Exception:
                pass

        now_ts = int(time.time())
        payload = {
            "guilds": guilds,
            "members": members,
            "online": online,
            "channels": channels,
            "threads": threads,
            "latency_ms": latency_ms,
            "cpu_percent": cpu_percent,
            "ram_mb": ram_mb,
            "ts": now_ts,
            # optional sticky fields if you use sticky updater elsewhere
        }
        self._last_payload = payload
        return payload

    # ---- writers ----
    def _write_file(self, payload: dict) -> None:
        try:
            p = Path(METRICS_FILE)
            p.parent.mkdir(parents=True, exist_ok=True)
            tmp = p.with_suffix(p.suffix + ".tmp")
            tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp.replace(p)
        except Exception as e:
            print(f"[metrics] write error: {e}")

    async def _push_http(self, payload: dict) -> None:
        if not PUSH_URL:
            return
        headers = {"Content-Type": "application/json"}
        if PUSH_TOKEN:
            headers["X-Token"] = PUSH_TOKEN

        # use stdlib to avoid extra deps; run in a thread
        def _post():
            import urllib.request
            import urllib.error
            req = urllib.request.Request(PUSH_URL, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=10) as resp:
                    resp.read()
            except Exception as e:
                print(f"[metrics] http push error: {e}")

        try:
            await asyncio.to_thread(_post)
        except Exception as e:
            print(f"[metrics] http push async error: {e}")

    # ---- loop ----
    @tasks.loop(seconds=PUSH_INTERVAL if PUSH_INTERVAL > 0 else 30)
    async def push_loop(self):
        payload = self._build_payload()
        # always write file (works when web and bot share the same FS/process)
        self._write_file(payload)
        # optionally push to dashboard over HTTP (for separate services like Render)
        await self._push_http(payload)

    @push_loop.before_loop
    async def _before(self):
        # wait until bot is ready
        try:
            await self.bot.wait_until_ready()
        except Exception:
            await asyncio.sleep(5)

async def setup(bot):
    await bot.add_cog(LiveMetricsPush(bot))
