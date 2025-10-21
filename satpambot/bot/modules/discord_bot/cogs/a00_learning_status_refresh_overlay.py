import os, json, asyncio, logging
from datetime import datetime, timezone
from typing import Optional, Dict, Tuple, List

import discord
from discord.ext import commands, tasks

log = logging.getLogger(__name__)

SENIOR_PHASES = ["SMP", "SMA", "KULIAH"]

def _parse_stage_key(k: str) -> int:
    k = str(k).strip().upper()
    for p in ("L","S"):
        if k.startswith(p):
            try:
                return int(k[len(p):])
            except Exception:
                pass
    try:
        return int(k)
    except Exception:
        return 999999

def _order_stages(d: Dict[str,int]) -> List[Tuple[str,int]]:
    return sorted(d.items(), key=lambda kv: _parse_stage_key(kv[0]))

class _Upstash:
    def __init__(self):
        self.url = os.getenv("UPSTASH_REDIS_REST_URL", "").rstrip("/")
        self.token = os.getenv("UPSTASH_REDIS_REST_TOKEN", "")
        self.enabled = bool(self.url and self.token and os.getenv("KV_BACKEND","").lower()=="upstash_rest")

    async def _get_json(self, session, path: str):
        import aiohttp
        headers = {"Authorization": f"Bearer {self.token}"}
        async with session.get(f"{self.url}{path}", headers=headers, timeout=15) as r:
            r.raise_for_status()
            return await r.json()

    async def get(self, session, key: str) -> Optional[str]:
        if not self.enabled: return None
        try:
            j = await self._get_json(session, f"/get/{key}")
            v = j.get("result")
            return None if v is None else str(v)
        except Exception:
            return None

    async def mset_pipeline(self, session, kv: Dict[str, str]) -> bool:
        """Write multiple keys atomically via pipeline to avoid URL-encoding issues."""
        if not self.enabled or not kv:
            return False
        import aiohttp
        headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
        commands = [["SET", str(k), str(v)] for k, v in kv.items()]
        async with session.post(f"{self.url}/pipeline", headers=headers, json=commands, timeout=15) as r:
            if r.status // 100 != 2:
                return False
            try:
                await r.json()
            except Exception:
                pass
            return True

upstash = _Upstash()

def _safe_int(x) -> int:
    if x is None: return 0
    if isinstance(x, (int, float)): return int(x)
    s = str(x).strip()
    if s.isdigit() or (s.startswith("-") and s[1:].isdigit()):
        return int(s)
    try:
        j = json.loads(s)
        if isinstance(j, dict) and "senior_total_xp" in j:
            return int(j["senior_total_xp"])
        if isinstance(j, dict) and "overall" in j:
            return int(j["overall"])
        if isinstance(j, (int, float)):
            return int(j)
    except Exception:
        pass
    return 0

def _compute_label_senior(senior_total: int, ladders: Dict[str, Dict[str,int]]):
    spent = 0
    for phase in SENIOR_PHASES:
        chunks = ladders.get(phase, {})
        for (stage, need) in _order_stages(chunks):
            need = max(1, int(need))
            have = max(0, senior_total - spent)
            if have < need:
                pct = 100.0 * (have / float(need))
                rem = max(0, need - have)
                return (f"{phase}-S{_parse_stage_key(stage)}", round(pct,1), rem)
            spent += need
    last = SENIOR_PHASES[-1]
    last_idx = len(_order_stages(ladders.get(last, {"S1":1})))
    return (f"{last}-S{last_idx}", 100.0, 0)

def _rank(label: str):
    tab = {p:i for i,p in enumerate(SENIOR_PHASES)}
    try:
        p, s = label.split("-",1)
    except ValueError:
        p, s = label, "S0"
    pi = tab.get(p, -1)
    try:
        si = int(s.upper().replace("S",""))
    except Exception:
        si = 0
    return (pi, si)

async def _get_floor_label(session) -> Optional[str]:
    env_min = os.getenv("LEARNING_MIN_LABEL", "").strip()
    if env_min: return env_min
    raw = await upstash.get(session, "learning:status_json")
    if not raw: return None
    try:
        return json.loads(raw).get("label")
    except Exception:
        return None

def _load_ladders_from_repo(script_file: str) -> Dict[str, Dict[str,int]]:
    # default to data/neuro-lite/ladder.json under repo root
    import os
    cur = os.path.abspath(os.path.dirname(script_file))
    for _ in range(10):
        cand = os.path.join(cur, "data", "neuro-lite", "ladder.json")
        if os.path.exists(cand):
            with open(cand, "r", encoding="utf-8") as f:
                j = json.load(f)
            ladders = {}
            for domain in ("junior","senior"):
                d = j.get(domain) or {}
                for phase, stages in d.items():
                    ladders[phase] = {str(k): int(v) for k,v in stages.items()}
            return ladders
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    return {}

class A00LearningStatusRefreshOverlay(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._period = max(60, int(os.getenv("LEARNING_REFRESH_PERIOD_SEC", "300") or "300"))
        self._ladders = _load_ladders_from_repo(__file__)
        self._task = self._loop.start()

    def cog_unload(self):
        try:
            self._loop.cancel()
        except Exception:
            pass

    @tasks.loop(seconds=30)
    async def _loop(self):
        if os.getenv("DISABLE_LEARNING_REFRESH"): return
        if not upstash.enabled: return
        now = datetime.now(timezone.utc)
        if int(now.timestamp()) % self._period != 0:
            return
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                raw_total = await upstash.get(session, "xp:bot:senior_total")
                senior_total = _safe_int(raw_total)
                label, percent, remaining = _compute_label_senior(senior_total, self._ladders)
                floor = await _get_floor_label(session)
                if floor and _rank(label) < _rank(floor):
                    label = floor
                phase = label.split("-")[0]
                status = f"{label} ({percent:.1f}%)"
                status_json = json.dumps({"label":label,"percent":percent,"remaining":remaining,"senior_total":senior_total}, separators=(",",":"))
                await upstash.mset_pipeline(session, {
                    "learning:status": status,
                    "learning:status_json": status_json,
                    "learning:phase": phase
                })
        except Exception as e:
            log.warning("[learning refresh] skipped: %s", e)

    @_loop.before_loop
    async def _before(self):
        await self.bot.wait_until_ready()
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                raw_total = await upstash.get(session, "xp:bot:senior_total")
                senior_total = _safe_int(raw_total)
                label, percent, remaining = _compute_label_senior(senior_total, self._ladders)
                floor = await _get_floor_label(session)
                if floor and _rank(label) < _rank(floor):
                    label = floor
                phase = label.split("-")[0]
                status = f"{label} ({percent:.1f}%)"
                status_json = json.dumps({"label":label,"percent":percent,"remaining":remaining,"senior_total":senior_total}, separators=(",",":"))
                await upstash.mset_pipeline(session, {
                    "learning:status": status,
                    "learning:status_json": status_json,
                    "learning:phase": phase
                })
        except Exception:
            pass

async def setup(bot: commands.Bot):
    await bot.add_cog(A00LearningStatusRefreshOverlay(bot))
