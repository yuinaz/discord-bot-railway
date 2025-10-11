
from __future__ import annotations
import os, json, time, logging, random
from pathlib import Path
from typing import Dict, Any
from datetime import datetime, timedelta, timezone

import discord
from discord.ext import commands

log = logging.getLogger(__name__)

BASE = Path(os.getenv("NEURO_BRIDGE_DIR", "data/neuro-lite"))
BASE.mkdir(parents=True, exist_ok=True)
J_PATH = BASE / "bridge_junior.json"
S_PATH = BASE / "bridge_senior.json"
OVERRIDE_PATH = BASE / "bridge_override.json"     # {"split":{"junior":0,"senior":1},"ts":...}
WEEKEND_PATH  = BASE / "xp_weekend_boost.json"    # {"tz":"Asia/Jakarta","schedule":{"YYYY-MM-DD":{"sat":2,"sun":4}}}

# Parse base split config: "junior:1,senior:1"
_SPLIT = os.getenv("NEURO_BRIDGE_XP_SPLIT", "junior:1,senior:1")
SPLIT_BASE: Dict[str, int] = {}
for part in _SPLIT.split(","):
    part = part.strip()
    if not part:
        continue
    try:
        name, val = part.split(":")
        SPLIT_BASE[name.strip()] = max(0, int(val))
    except Exception:
        pass
if not SPLIT_BASE:
    SPLIT_BASE = {"junior": 1, "senior": 1}

def _load_json(p: Path, default: Dict[str, Any]) -> Dict[str, Any]:
    if not p.exists():
        try:
            p.write_text(json.dumps(default, indent=2), encoding="utf-8")
        except Exception:
            pass
        return json.loads(json.dumps(default))
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return json.loads(json.dumps(default))

def _save_json(p: Path, data: Dict[str, Any]):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")

def _current_split() -> Dict[str,int]:
    d = _load_json(OVERRIDE_PATH, {"split": None})
    if isinstance(d.get("split"), dict):
        try:
            split = {k:int(v) for k,v in d["split"].items()}
            if any(v>0 for v in split.values()):
                return split
        except Exception:
            pass
    return dict(SPLIT_BASE)

def _add_xp(target: str, pts: int):
    path = J_PATH if target == "junior" else S_PATH
    d = _load_json(path, {"xp": 0, "updated": 0})
    d["xp"] = int(d.get("xp", 0)) + max(0, int(pts))
    d["updated"] = int(time.time())
    _save_json(path, d)
    return d["xp"]

# ---- Weekend multiplier logic (Asia/Jakarta) -------------------------------
def _tz_jakarta():
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo("Asia/Jakarta")
    except Exception:
        return timezone(timedelta(hours=7))

def _today_jakarta(test_dow: str | None = None):
    now = datetime.now(tz=_tz_jakarta())
    if test_dow:
        lw = test_dow.lower()
        if lw.startswith("sat"):
            class Fake(datetime):
                @property
                def weekday(self): return 5
            return Fake.fromtimestamp(now.timestamp(), tz=now.tzinfo)  # type: ignore
        if lw.startswith("sun"):
            class Fake(datetime):
                @property
                def weekday(self): return 6
            return Fake.fromtimestamp(now.timestamp(), tz=now.tzinfo)  # type: ignore
    return now

def _weekend_key(dt: datetime):
    wd = dt.weekday()
    if wd not in (5,6): return None
    if wd == 5:
        saturday = dt
    else:
        saturday = dt - timedelta(days=1)
    return saturday.date().isoformat()

def _ensure_weekend_pair(schedule: Dict[str, Any], key: str, choices: list[int]) -> Dict[str, Any]:
    if key in schedule and isinstance(schedule[key], dict):
        return schedule[key]
    if len(set(choices)) < 2:
        choices = [2,4,6]
    pair = random.sample(list(dict.fromkeys(choices)), 2)
    data = {"sat": int(pair[0]), "sun": int(pair[1])}
    schedule[key] = data
    return data

def _weekend_multiplier_now() -> int:
    enable = os.getenv("NEURO_WEEKEND_MULTIPLIER", "1").lower() not in ("0","false","no")
    if not enable: return 1
    test_dow = os.getenv("NEURO_WEEKEND_TEST_DOW")
    dt = _today_jakarta(test_dow)
    wd = dt.weekday()
    if wd not in (5,6): return 1
    data = _load_json(WEEKEND_PATH, {"tz":"Asia/Jakarta","schedule":{}})
    schedule = data.setdefault("schedule", {})
    try:
        CHOICES = [int(x.strip()) for x in os.getenv("NEURO_WEEKEND_CHOICES", "2,4,6").split(",") if x.strip()]
    except Exception:
        CHOICES = [2,4,6]
    key = _weekend_key(dt)
    if not key: return 1
    pair = _ensure_weekend_pair(schedule, key, CHOICES)
    data["tz"] = "Asia/Jakarta"
    _save_json(WEEKEND_PATH, data)
    return int(pair["sat" if wd==5 else "sun"])

# ---------------------------------------------------------------------------

class NeuroCurriculumBridge(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        log.info("[bridge] ready; base_split=%s", SPLIT_BASE)

    @commands.Cog.listener()
    async def on_neuro_xp(self, payload: Dict[str, Any]):
        try:
            pts = max(0, int(payload.get("points", 0)))
            src = str(payload.get("source", "unknown"))
            ch  = int(payload.get("channel_id", 0))
        except Exception:
            return
        if pts <= 0:
            return

        mult = _weekend_multiplier_now()
        eff_pts = pts * mult
        if mult > 1:
            log.info("[bridge] weekend multiplier x%s active -> %s -> %s (src=%s ch=%s)", mult, pts, eff_pts, src, ch)

        split = _current_split()
        total_weight = sum(split.values()) or 1

        for target, w in split.items():
            add = int(round(eff_pts * (w / total_weight)))
            if add <= 0: continue
            new_total = _add_xp("junior" if target == "junior" else "senior", add)
            try:
                self.bot.dispatch("neuro_curriculum_progress", {
                    "target": target, "delta": add, "total": new_total,
                    "source": src, "channel_id": ch, "multiplier": mult, "split": split
                })
            except Exception:
                pass

async def setup(bot: commands.Bot):
    await bot.add_cog(NeuroCurriculumBridge(bot))
