import os, json, logging
from typing import Dict, Tuple, Optional
from discord.ext import commands, tasks
import discord

log = logging.getLogger(__name__)

DEFAULT_LADDER = {
    "KULIAH": {"S1": 19000, "S2": 35000, "S3": 58000, "S4": 70000, "S5": 96500, "S6": 158000, "S7": 220000, "S8": 262500},
    "MAGANG": {"1TH": 2000000},
}

def _pick_env(k: str) -> Optional[str]:
    v = os.getenv(k)
    if v: return v
    if k == "UPSTASH_REST_URL":
        return os.getenv("UPSTASH_REDIS_REST_URL")
    if k == "UPSTASH_REST_TOKEN":
        return os.getenv("UPSTASH_REDIS_REST_TOKEN")
    return None

async def _rest_get_json(url: str, token: str, path: str) -> Optional[dict]:
    try:
        import httpx
    except Exception:
        return None
    try:
        async with httpx.AsyncClient(timeout=6) as cli:
            r = await cli.get(f"{url}/{path}", headers={"Authorization": f"Bearer {token}"})
            if r.status_code // 100 != 2:
                return None
            return r.json()
    except Exception:
        return None

async def _fetch_total_xp() -> Optional[int]:
    url = _pick_env("UPSTASH_REST_URL")
    tok = _pick_env("UPSTASH_REST_TOKEN")
    key = os.getenv("XP_SENIOR_KEY", "xp:bot:senior_total_v2")
    if not (url and tok and key):
        return None
    data = await _rest_get_json(url, tok, f"get/{key}")
    if not data: return None
    res = data.get("result")
    try:
        return int(str(res))
    except Exception:
        return None

async def _fetch_hash(key: str) -> Dict[str,int]:
    # Try Upstash hash first
    url = _pick_env("UPSTASH_REST_URL")
    tok = _pick_env("UPSTASH_REST_TOKEN")
    if url and tok:
        data = await _rest_get_json(url, tok, f"hgetall/{key}")
        if data and isinstance(data.get("result"), list):
            arr = data["result"]
            mp = {}
            for i in range(0, len(arr), 2):
                try:
                    mp[str(arr[i])] = int(str(arr[i+1]))
                except Exception:
                    pass
            if mp:
                return mp

    # Fallback to local file
    try:
        ladder_file = os.getenv("LADDER_FILE", "data/neuro-lite/ladder.json")
        with open(ladder_file, "r", encoding="utf-8") as f:
            j = json.load(f)
            # support both senior.KULIAH and top-level KULIAH
            if "KULIAH" in key:
                return j.get("senior", {}).get("KULIAH") or j.get("KULIAH") or DEFAULT_LADDER["KULIAH"]
            if "MAGANG" in key:
                return j.get("senior", {}).get("MAGANG") or j.get("MAGANG") or DEFAULT_LADDER["MAGANG"]
    except Exception:
        pass
    # default minimal
    if "KULIAH" in key: return DEFAULT_LADDER["KULIAH"]
    if "MAGANG" in key: return DEFAULT_LADDER["MAGANG"]
    return {}

def _calc_kuliah(total: int, mapping: Dict[str,int]) -> Tuple[str, int, int, int]:
    # returns (stage_name, lower, upper, pct)
    pairs = []
    for name, thr in mapping.items():
        try:
            pairs.append((name, int(thr)))
        except Exception:
            continue
    pairs.sort(key=lambda x: x[1])
    stage = pairs[0][0]
    low = 0
    high = pairs[0][1]
    for i, (name, thr) in enumerate(pairs):
        if total >= thr:
            stage = name
            low = thr
            high = pairs[i+1][1] if i+1 < len(pairs) else thr
        else:
            high = thr
            break
    denom = max(1, (high - low))
    pct = max(0, min(100, int((total - low) * 100 / denom)))
    return stage, low, high, pct

def _calc_magang(total: int, mapping: Dict[str,int]) -> Tuple[int, int, bool]:
    thr = mapping.get("1TH")
    if thr is None:
        # fallback ke max value di mapping
        thr = 0
        for v in mapping.values():
            try:
                thr = max(thr, int(v))
            except Exception:
                pass
    thr = int(thr)
    done = total >= thr
    remain = max(0, thr - total)
    pct = max(0, min(100, int(total * 100 / thr))) if thr > 0 else 0
    return pct, remain, done

class XpLadderReporter(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._once.start()

    def cog_unload(self):
        self._once.cancel()

    @tasks.loop(count=1)
    async def _once(self):
        total = await _fetch_total_xp()
        kuliah = await _fetch_hash("xp:ladder:KULIAH")
        magang = await _fetch_hash("xp:ladder:MAGANG")
        if total is None:
            log.info("[xp-ladder] total_xp=? (Upstash not configured)")
            return
        stage, low, high, pct = _calc_kuliah(total, kuliah)
        mpct, mremain, mdone = _calc_magang(total, magang)
        rng = f"{low}..{high if high>low else '∞'}"
        log.info("[xp-ladder] total=%s -> KULIAH-%s (band %s, %s%%)", total, stage, rng, pct)
        thr = magang.get("1TH", 2000000)
        if mdone:
            log.info("[xp-ladder] MAGANG: LULUS (>= %s)", thr)
        else:
            log.info("[xp-ladder] MAGANG: progress %s%%, remaining %s (target %s)", mpct, mremain, thr)

    @_once.before_loop
    async def _wait(self):
        await self.bot.wait_until_ready()

    @commands.hybrid_command(name="xp_ladder", with_app_command=True, description="Show XP status for KULIAH & MAGANG")
    async def xp_ladder(self, ctx: commands.Context):
        total = await _fetch_total_xp()
        kuliah = await _fetch_hash("xp:ladder:KULIAH")
        magang = await _fetch_hash("xp:ladder:MAGANG")
        if total is None:
            await ctx.reply("Upstash belum terkonfigurasi.", ephemeral=True)
            return
        stage, low, high, pct = _calc_kuliah(total, kuliah)
        mpct, mremain, mdone = _calc_magang(total, magang)
        thr = magang.get("1TH", 2000000)
        desc = f"**Total XP**: {total}\n**KULIAH**: {stage}  — band {low}..{('∞' if high==low else high)}  — progress {pct}%\n**MAGANG**: {'LULUS ✅' if mdone else f'progress {mpct}% (sisa {mremain} / target {thr})'}"
        emb = discord.Embed(title="XP Ladder Status", description=desc)
        await ctx.reply(embed=emb, ephemeral=True)

async def setup(bot):
    await bot.add_cog(XpLadderReporter(bot))
