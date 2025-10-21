
from __future__ import annotations
import os, json, logging, asyncio
from pathlib import Path
from discord.ext import commands
try:
    import httpx
except Exception:
    httpx = None

log = logging.getLogger(__name__)

def _compute(total: int, senior: dict):
    running = int(total or 0)
    for g, levels in senior.items():
        for lvl, cost in levels.items():
            cost = int(cost)
            if running < cost:
                pct = round((running / cost) * 100.0, 1) if cost > 0 else 100.0
                return f"{g}-{lvl}", pct, (cost - running)
            running -= cost
    last_g = list(senior.keys())[-1]
    last_l = list(senior[last_g].keys())[-1]
    return f"{last_g}-{last_l}", 100.0, 0

class LearningStatusRefresh(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        try:
            await self._refresh_once()
        except Exception as e:
            log.debug("[learning-status] refresh failed: %r", e)

    async def _refresh_once(self):
        LADDER_PATH = Path(os.getenv("LADDER_PATH", "data/neuro-lite/ladder.json"))
        URL = os.getenv("UPSTASH_REDIS_REST_URL", "").rstrip("/")
        TOK = os.getenv("UPSTASH_REDIS_REST_TOKEN", "")
        if not (URL and TOK and httpx and LADDER_PATH.exists()):
            log.info("[learning-status] skip: missing env/httpx or ladder.json not found")
            return
        ladder = json.loads(LADDER_PATH.read_text("utf-8"))
        senior = ladder.get("senior") or {}
        async with httpx.AsyncClient(timeout=15) as x:
            r = await x.get(f"{URL}/get/xp:bot:senior_total", headers={"Authorization": f"Bearer {TOK}"})
            raw = (r.json() or {}).get("result")
            try:
                total = int(raw)
            except Exception:
                try:
                    total = int(json.loads(raw).get("senior_total_xp", 0))
                except Exception:
                    total = 0
            label, pct, remaining = _compute(total, senior)
            status = f"{label} ({pct}%)"
            status_json = json.dumps({"label": label, "percent": float(pct), "remaining": int(remaining), "senior_total": int(total)}, separators=(",", ":"))
            await x.post(f"{URL}/pipeline", headers={"Authorization": f"Bearer {TOK}", "Content-Type": "application/json"}, json=[["SET", "learning:status", status], ["SET", "learning:status_json", status_json]])
            log.info("[learning-status] refreshed -> %s", status)

async def setup(bot: commands.Bot):
    try:
        await bot.add_cog(LearningStatusRefresh(bot))
    except Exception as e:
        log = logging.getLogger(__name__)
        log.debug("[learning-status] setup failed: %r", e)
