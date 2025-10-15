
from __future__ import annotations
import os, json, time, logging
from pathlib import Path
from typing import Dict, List, Tuple
import discord
from discord.ext import commands, tasks

log = logging.getLogger(__name__)

BASE = Path(os.getenv("NEURO_BRIDGE_DIR", "data/neuro-lite"))
BASE.mkdir(parents=True, exist_ok=True)
J_PATH = BASE / "bridge_junior.json"
S_PATH = BASE / "bridge_senior.json"
LP_J = BASE / "learn_progress_junior.json"
LP_S = BASE / "learn_progress_senior.json"
GATE_PATH = BASE / "gate_status.json"
LADDER_PATH = BASE / "ladder.json"

PERIOD = int(os.getenv("NEURO_PROGRESS_PERIOD", "180"))
DEFAULT_LADDER = {
    "junior": {"TK": {"L1": 100, "L2": 150}},
    "senior": {"SD": {"L1": 150, "L2": 250, "L3": 400, "L4": 600, "L5": 800, "L6": 1000}},
}

def _load_json(p: Path, default):
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(default, indent=2))
        return json.loads(json.dumps(default))
    try:
        return json.loads(p.read_text())
    except Exception:
        return json.loads(json.dumps(default))

def _save_json(p: Path, data):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2))

def _ladder() -> Dict:
    return _load_json(LADDER_PATH, DEFAULT_LADDER)

def _split_levels(total_xp: int, stages: Dict[str, int]):
    out = {}; rem = int(total_xp)
    keys = list(stages.keys())
    for k in keys:
        need = max(1, int(stages[k]))
        if rem <= 0:
            out[k] = 0
        elif rem >= need:
            out[k] = 100; rem -= need
        else:
            out[k] = int(max(0, min(100, round(100 * (rem / need))))); rem = 0
    overall = int(round(sum(out.values()) / max(1, len(out))))
    return out, overall

class NeuroProgressMapper(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._task.start()
        log.info("[progress-mapper] started; period=%ss", PERIOD)

    def cog_unload(self):
        try: self._task.cancel()
        except Exception: pass

    @tasks.loop(seconds=PERIOD)
    async def _task(self):
        try:
            self._update_once()
        except Exception:
            log.exception("[progress-mapper] update error")

    def _update_once(self):
        ladd = _ladder()
        bj = _load_json(J_PATH, {"xp":0,"updated":0})
        bs = _load_json(S_PATH, {"xp":0,"updated":0})
        j_xp = int(bj.get("xp", 0)); s_xp = int(bs.get("xp", 0))

        j_tree = {}; j_overalls = []
        for block, levels in ladd.get("junior", {}).items():
            perc, ov = _split_levels(j_xp, levels)
            j_tree[block] = perc; j_overalls.append(ov)
        j_overall = int(round(sum(j_overalls)/max(1,len(j_overalls)))) if j_overalls else 0
        _save_json(LP_J, {"overall": j_overall, **j_tree})

        s_tree = {}; s_overalls = []
        for block, levels in ladd.get("senior", {}).items():
            perc, ov = _split_levels(s_xp, levels)
            s_tree[block] = perc; s_overalls.append(ov)
        s_overall = int(round(sum(s_overalls)/max(1,len(s_overalls)))) if s_overalls else 0
        _save_json(LP_S, {"overall": s_overall, **s_tree})

        gate = {"promotion_allowed": bool(j_overall >= 100), "ts": int(time.time())}
        _save_json(GATE_PATH, gate)

async def setup(bot: commands.Bot):
    await bot.add_cog(NeuroProgressMapper(bot))