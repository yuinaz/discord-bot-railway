
import os, json, logging
from typing import Dict, Tuple, Optional, List
from discord.ext import commands, tasks
import discord

log = logging.getLogger(__name__)

def _env_pick(k: str) -> Optional[str]:
    v = os.getenv(k)
    if v: return v
    if k == "UPSTASH_REST_URL":
        return os.getenv("UPSTASH_REDIS_REST_URL")
    if k == "UPSTASH_REST_TOKEN":
        return os.getenv("UPSTASH_REDIS_REST_TOKEN")
    return None

async def _rest_get_json(path: str):
    try:
        import httpx
    except Exception:
        return None
    url = _env_pick("UPSTASH_REST_URL")
    tok = _env_pick("UPSTASH_REST_TOKEN")
    if not (url and tok):
        return None
    try:
        async with httpx.AsyncClient(timeout=6) as cli:
            r = await cli.get(f"{url}/{path}", headers={"Authorization": f"Bearer {tok}"})
            if r.status_code // 100 != 2:
                return None
            return r.json()
    except Exception:
        return None

async def _rest_get(path: str):
    j = await _rest_get_json(path)
    if not j: return None
    return j.get("result")

async def _rest_set(path: str) -> bool:
    j = await _rest_get_json(path)
    return j is not None

async def _fetch_hash(key: str) -> Dict[str,int]:
    j = await _rest_get_json(f"hgetall/{key}")
    if j and isinstance(j.get("result"), list):
        arr = j["result"]
        mp = {}
        for i in range(0, len(arr), 2):
            try:
                mp[str(arr[i])] = int(str(arr[i+1]))
            except Exception:
                pass
        if mp:
            return mp
    try:
        ladder_file = os.getenv("LADDER_FILE", "data/neuro-lite/ladder.json")
        with open(ladder_file, "r", encoding="utf-8") as f:
            J = json.load(f)
            if "KULIAH" in key:
                return J.get("senior", {}).get("KULIAH") or J.get("KULIAH") or {}
            if "MAGANG" in key:
                return J.get("senior", {}).get("MAGANG") or J.get("MAGANG") or {}
    except Exception:
        pass
    return {}

async def _get_total_xp():
    key = os.getenv("XP_SENIOR_KEY", "xp:bot:senior_total_v2")
    v = await _rest_get(f"get/{key}")
    if v is None:
        return None
    try:
        return int(str(v))
    except Exception:
        return None

def _pairs_sorted(mp: Dict[str,int]) -> List[Tuple[str,int]]:
    items = []
    for k,v in mp.items():
        try:
            items.append((k, int(v)))
        except Exception:
            pass
    items.sort(key=lambda x: x[1])
    return items

def _current_kuliah_stage(total: int, kuliah_map: Dict[str,int]) -> Tuple[str,int,int]:
    pairs = _pairs_sorted(kuliah_map) or [
        ("S1", 19000), ("S2", 35000), ("S3", 58000), ("S4", 70000),
        ("S5", 96500), ("S6", 158000), ("S7", 220000), ("S8", 262500)
    ]
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
    return stage, low, high

def _stage_target(stage: str, kuliah_map: Dict[str,int]) -> int:
    try:
        return int(kuliah_map[stage])
    except Exception:
        fallback = {
            "S1": 19000, "S2": 35000, "S3": 58000, "S4": 70000,
            "S5": 96500, "S6": 158000, "S7": 220000, "S8": 262500
        }
        return int(fallback.get(stage, 0))

def _magang_target(magang_map: Dict[str,int]) -> int:
    if "1TH" in magang_map:
        try:
            return int(magang_map["1TH"])
        except Exception:
            pass
    mx = 0
    for v in magang_map.values():
        try: mx = max(mx, int(v))
        except Exception: pass
    return mx if mx > 0 else 2000000

BASE_PREFIX = "xp:sr"
def _k(x): return f"{BASE_PREFIX}:{x}"

async def _read_state() -> Dict[str, str]:
    items = {}
    for k in ("mode","stage","baseline","target"):
        v = await _rest_get(f"get/{_k(k)}")
        if v is not None:
            items[k] = str(v)
    return items

async def _write_state(stage: str, baseline: int, target: int, mode: str="stage_reset") -> None:
    await _rest_set(f"set/{_k('mode')}/{mode}")
    await _rest_set(f"set/{_k('stage')}/{stage}")
    await _rest_set(f"set/{_k('baseline')}/{baseline}")
    await _rest_set(f"set/{_k('target')}/{target}")

async def _write_status(label: str, pct: float, remaining: int, total: int) -> None:
    pct = round(pct, 1)
    remaining = max(0, int(remaining))
    await _rest_set(f"set/learning:status/{label} ({pct}%)")
    data = json.dumps({"label": label, "percent": pct, "remaining": remaining, "senior_total": total})
    await _rest_set(f"set/learning:status_json/{data}")

class KuliahStageResetOverlay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.task.start()

    def cog_unload(self):
        self.task.cancel()

    @tasks.loop(seconds=15.0)
    async def task(self):
        total = await _get_total_xp()
        if total is None:
            return
        kuliah = await _fetch_hash("xp:ladder:KULIAH")
        magang = await _fetch_hash("xp:ladder:MAGANG")

        s = await _read_state()
        mode = s.get("mode", "stage_reset")
        stage = s.get("stage")
        baseline = int(s.get("baseline", "0") or "0")
        target = int(s.get("target", "0") or "0")

        if not stage or baseline == 0 or target == 0:
            cur_stage, entry_thr, _ = _current_kuliah_stage(total, kuliah)
            init_mode = (os.getenv("INIT_BASELINE_MODE") or "entry_threshold").lower()
            baseline = total if init_mode == "now" else entry_thr
            stage = cur_stage
            target = _stage_target(stage, kuliah)
            await _write_state(stage, baseline, target, mode)
            prog = max(0, total - baseline)
            pct = min(100.0, (prog * 100.0) / target if target > 0 else 0.0)
            await _write_status(f"KULIAH-{stage}", pct, target - prog, total)
            log.info("[kuliah-stage] init stage=%s baseline=%s target=%s pct=%.1f", stage, baseline, target, pct)
            return

        s8_cap = max(_pairs_sorted(kuliah), key=lambda x: x[1])[1] if kuliah else 262500
        if total < s8_cap:
            prog = max(0, total - baseline)
            if prog >= target:
                ordered = [name for name,_ in _pairs_sorted(kuliah)]
                try:
                    idx = ordered.index(stage)
                except ValueError:
                    idx = 0
                if idx + 1 < len(ordered):
                    stage = ordered[idx+1]
                baseline = total
                target = _stage_target(stage, kuliah)
                await _write_state(stage, baseline, target, mode)
                log.info("[kuliah-stage] advanced to %s (baseline=%s target=%s)", stage, baseline, target)
                prog = 0
            pct = min(100.0, (prog * 100.0)/target if target>0 else 0.0)
            await _write_status(f"KULIAH-{stage}", pct, target - prog, total)
        else:
            mtarget = _magang_target(magang)
            mp = max(0, total)
            mdone = mp >= mtarget
            mpct = min(100.0, (mp * 100.0)/mtarget if mtarget>0 else 0.0)
            label = "MAGANG-1TH" + (" LULUS" if mdone else "")
            await _write_status(label, mpct, mtarget - mp, total)

    @task.before_loop
    async def _wait(self):
        await self.bot.wait_until_ready()

    @commands.hybrid_command(name="xp_stage", with_app_command=True, description="Stage-reset KULIAH (MAGANG after S8)")
    async def xp_stage(self, ctx: commands.Context):
        s = await _read_state()
        total = await _get_total_xp() or 0
        stage = s.get("stage") or "?"
        baseline = int(s.get("baseline", "0") or "0")
        target = int(s.get("target", "0") or "0")
        prog = max(0, total - baseline)
        pct = min(100, int((prog * 100) / target)) if target>0 else 0
        desc = f"**Total XP**: {total}\\n**Stage**: KULIAH-{stage}\\n**Target**: {target}\\n**Progress (reset)**: {prog} / {target} ({pct}%)"
        emb = discord.Embed(title="KULIAH Stage (Reset Mode)", description=desc)
        await ctx.reply(embed=emb, ephemeral=True)

async def setup(bot):
    await bot.add_cog(KuliahStageResetOverlay(bot))
