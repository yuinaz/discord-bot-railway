# a08_learning_status_autopin_overlay.py
from __future__ import annotations
import os, json, logging
from pathlib import Path
from discord.ext import commands, tasks

try:
    import httpx
except Exception:
    httpx = None

log = logging.getLogger(__name__)

UPSTASH_URL = os.getenv("UPSTASH_REDIS_REST_URL","").rstrip("/")
UPSTASH_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN","")
LADDER_PATH = Path(os.getenv("LADDER_PATH","data/neuro-lite/ladder.json"))
INTERVAL = int(os.getenv("LEARNING_STATUS_INTERVAL","600"))  # 10 menit

def _load_ladder():
    try:
        data = json.loads(LADDER_PATH.read_text("utf-8"))
        return data.get("senior") or {}
    except Exception as e:
        log.warning("[learn-status] cannot load ladder: %r", e)
        return {}

def _compute(total: int, senior: dict):
    running = int(total or 0)
    for group_name, levels in senior.items():
        for lvl_name, cost in levels.items():
            cost = int(cost)
            if running < cost:
                percent = round((running / cost) * 100.0, 1) if cost > 0 else 100.0
                remaining = cost - running
                return f"{group_name}-{lvl_name}", percent, remaining
            running -= cost
    # exceed all
    if senior:
        last_g = list(senior.keys())[-1]
        last_l = list(senior[last_g].keys())[-1]
        return f"{last_g}-{last_l}", 100.0, 0
    return "TK-L1", 0.0, 0

class LearningStatusAuto(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.senior = _load_ladder()
        if httpx and UPSTASH_URL and UPSTASH_TOKEN:
            self.job.start()
        else:
            log.info("[learn-status] httpx/UPSTASH env missing; auto-refresh disabled")

    def cog_unload(self):
        try: self.job.cancel()
        except Exception: pass

    @tasks.loop(seconds=INTERVAL)
    async def job(self):
        try:
            async with httpx.AsyncClient(timeout=15.0) as cli:
                r = await cli.get(f"{UPSTASH_URL}/get/xp:bot:senior_total",
                                  headers={"Authorization": f"Bearer {UPSTASH_TOKEN}"})
                r.raise_for_status()
                raw = r.json().get("result")
                try:
                    total = int(raw)
                except Exception:
                    try:
                        total = int(json.loads(raw).get("senior_total_xp",0))
                    except Exception:
                        total = 0
                label, pct, remaining = _compute(total, self.senior)
                status = f"{label} ({pct}%)"
                status_json = json.dumps({
                    "label": label, "percent": float(pct),
                    "remaining": int(remaining), "senior_total": int(total)
                }, separators=(",",":"))
                cmds = [
                    ["SET","learning:status", status],
                    ["SET","learning:status_json", status_json],
                ]
                wr = await cli.post(f"{UPSTASH_URL}/pipeline",
                                    headers={"Authorization": f"Bearer {UPSTASH_TOKEN}",
                                             "Content-Type":"application/json"},
                                    json=cmds)
                wr.raise_for_status()
                log.info("[learn-status] %s", status)
        except Exception as e:
            log.warning("[learn-status] refresh failed: %r", e)

    @job.before_loop
    async def before(self):
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot):
    await bot.add_cog(LearningStatusAuto(bot))
