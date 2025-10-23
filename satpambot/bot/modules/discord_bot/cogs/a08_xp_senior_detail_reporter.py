
from discord.ext import commands
"""
a08_xp_senior_detail_reporter.py
Menghitung ringkasan XP senior & menulis dua key:
- SET "xp:bot:senior_total" (INT)     → kompatibel bootstrap
- SET "xp:bot:senior_detail" (JSON)   → breakdown (levels/reasons/top_users)

Sumber data upstash:
- HGETALL "xp:bucket:senior:users"  (dibangun oleh verbose sink)
- HGETALL "xp:bucket:reasons"

ENV:
  UPSTASH_REDIS_REST_URL, UPSTASH_REDIS_REST_TOKEN
  SENIOR_L1_TARGET=2000
  SENIOR_DETAIL_INTERVAL=300
  SENIOR_DETAIL_TOPN=10
"""
import os, json, time, logging
from discord.ext import tasks, commands

log = logging.getLogger(__name__)

def _env_int(k, d):
    try: return int(os.getenv(k, d))
    except Exception: return d

UPSTASH_URL = os.getenv("UPSTASH_REDIS_REST_URL","").rstrip("/")
UPSTASH_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN","")
L1_TARGET = _env_int("SENIOR_L1_TARGET", 2000)
INTERVAL = _env_int("SENIOR_DETAIL_INTERVAL", 300)
TOPN = _env_int("SENIOR_DETAIL_TOPN", 10)

class _Upstash:
    def __init__(self, url: str, token: str):
        self.url = url
        self.token = token
    async def pipeline(self, commands):
        import httpx
        if not self.url or not self.token:
            return None
        try:
            async with httpx.AsyncClient(timeout=8.0) as cli:
                r = await cli.post(f"{self.url}/pipeline", json=commands, headers={
                    "Authorization": f"Bearer {self.token}"
                })
                r.raise_for_status()
                return r.json()
        except Exception as e:
            log.warning("[senior-detail] pipeline failed: %r", e)
            return None

def _res(x):
    if isinstance(x, dict) and "result" in x:
        return x["result"]
    return x

def _pairs_to_dict(lst):
    d = {}
    if isinstance(lst, list):
        it = iter(lst)
        for k in it:
            try:
                v = next(it)
            except StopIteration:
                break
            try:
                d[str(k)] = int(v)
            except Exception:
                try:
                    d[str(k)] = int(float(v))
                except Exception:
                    d[str(k)] = 0
    return d

class SeniorDetailReporter(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = _Upstash(UPSTASH_URL, UPSTASH_TOKEN)
        self.task.start()

    def cog_unload(self):
        try: self.task.cancel()
        except Exception: pass

    @tasks.loop(seconds=INTERVAL)
    async def task(self):
        if not (UPSTASH_URL and UPSTASH_TOKEN):
            return
        cmds = [
            ["HGETALL", "xp:bucket:senior:users"],
            ["HGETALL", "xp:bucket:reasons"],
        ]
        res = await self.db.pipeline(cmds) or []
        senior_users = _pairs_to_dict(_res(res[0]) if len(res)>0 else [])
        reasons      = _pairs_to_dict(_res(res[1]) if len(res)>1 else [])

        total = sum(senior_users.values()) if senior_users else 0
        l1 = min(total, max(0, L1_TARGET))
        l2 = max(0, total - l1)
        top_users = sorted(senior_users.items(), key=lambda kv: kv[1], reverse=True)[:TOPN]

        payload = {
            "senior_total_xp": total,
            "levels": {"L1": l1, "L2": l2},
            "reasons": reasons,
            "top_users": [{"uid": k, "xp": v} for k, v in top_users],
            "last_update": time.strftime("%Y-%m-%dT%H:%M:%S")
        }
        j = json.dumps(payload, separators=(",",":"))
        cmds2 = [
            ["SET", "xp:bot:senior_detail", j],
            ["SET", "xp:bot:senior_total", str(total)],
        ]
        await self.db.pipeline(cmds2)

    @task.before_loop
    async def before(self):
        await self.bot.wait_until_ready()
async def setup(bot):
    await bot.add_cog(SeniorDetailReporter(bot))

def setup(bot):
    try:
        import asyncio
        if asyncio.get_event_loop().is_running():
            return asyncio.create_task(bot.add_cog(SeniorDetailReporter(bot)))
    except Exception:
        pass
    return bot.add_cog(SeniorDetailReporter(bot))