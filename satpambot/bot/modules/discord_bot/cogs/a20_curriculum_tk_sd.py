from discord.ext import commands
import os, json, logging
from typing import Dict, Tuple
from datetime import datetime, timezone

import discord
from discord.ext import tasks

from ..helpers.upstash_client import UpstashClient
from ..helpers.ladder_loader import load_ladders, parse_stage_idx

log = logging.getLogger(__name__)

JUNIOR_PHASES = ["TK", "SD"]

def _order_stages(d: Dict[str,int]):
    return sorted(d.items(), key=lambda kv: parse_stage_idx(kv[0]))

def _compute_junior_label(total: int, ladders: Dict[str, Dict[str,int]]) -> Tuple[str, float, int]:
    spent = 0
    for phase in JUNIOR_PHASES:
        chunks = ladders.get(phase, {})
        for (stage, need) in _order_stages(chunks):
            need = max(1, int(need))
            have = max(0, total - spent)
            if have < need:
                pct = 100.0 * (have / float(need))
                rem = max(0, need - have)
                return (f"{phase}-S{parse_stage_idx(stage)}", round(pct,1), rem)
            spent += need
    last = JUNIOR_PHASES[-1]
    last_idx = len(_order_stages(ladders.get(last, {"S1":1})))
    return (f"{last}-S{last_idx}", 100.0, 0)

def _load_cfg():
    try:
        cid = int(os.getenv("LEINA_CURRICULUM_CHANNEL_ID","") or "0") or None
    except Exception:
        cid = None
    return {"report_channel_id": cid}

class CurriculumTKSD(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.client = UpstashClient()
        self.ladders = load_ladders(__file__)
        self.period = max(60, int(os.getenv("LEINA_CURRICULUM_PERIOD_SEC","300") or "300"))
        self.template = os.getenv("LEINA_CURRICULUM_TEMPLATE", "📘 {label} • {percent:.1f}% (TK/SD)")
        cfg = _load_cfg()
        self.channel_id = cfg.get("report_channel_id")
        self._last_text = None
        if self.channel_id and self.client.enabled:
            self.loop.start()

    def cog_unload(self):
        try: self.loop.cancel()
        except Exception: pass

    async def _read_state(self) -> Tuple[str, float]:
        total = 0
        if self.client.enabled:
            try:
                raw = await self.client.get_raw("xp:bot:junior_total")
                if raw is not None:
                    try: total = int(raw)
                    except Exception:
                        try: total = int(json.loads(raw).get("overall", 0))
                        except Exception: total = 0
            except Exception:
                total = 0
        label, pct, _ = _compute_junior_label(int(total), self.ladders or {})
        return (label, pct)

    @tasks.loop(seconds=30)
    async def loop(self):
        if not self.client.enabled or not self.channel_id:
            return
        now = datetime.now(timezone.utc)
        if int(now.timestamp()) % self.period != 0:
            return
        try:
            ch = self.bot.get_channel(self.channel_id) or await self.bot.fetch_channel(self.channel_id)
            if not ch: return
            label, pct = await self._read_state()
            text = self.template.format(label=label, percent=pct)
            if text == self._last_text: return
            await ch.send(text)
            self._last_text = text
        except Exception:
            pass

    @loop.before_loop
    async def _before(self):
        await self.bot.wait_until_ready()

    @commands.command(name="kurjunior")
    async def cmd_kurjunior(self, ctx: commands.Context):
        label, pct = await self._read_state()
        await ctx.send(self.template.format(label=label, percent=pct))
async def setup(bot: commands.Bot):
    await bot.add_cog(CurriculumTKSD(bot))

# === compat shims for TK overlays (safe, no format change) ===
from os import getenv
from pathlib import Path
try:
    import httpx  # type: ignore
except Exception:
    httpx = None

PROGRESS_FILE = getenv("TKPROGRESS_FILE", "data/neuro-lite/tk_progress.json")

async def _probe_total_xp_runtime(bot=None):
    try:
        url = getenv("UPSTASH_REST_URL") or getenv("UPSTASH_REDIS_REST_URL")
        tok = getenv("UPSTASH_REST_TOKEN") or getenv("UPSTASH_REDIS_REST_TOKEN")
        key = getenv("XP_SENIOR_KEY", "xp:bot:senior_total_v2")
        if not (url and tok and key) or httpx is None:
            return None
        async with httpx.AsyncClient(timeout=5) as cli:
            r = await cli.get(f"{url}/get/{key}", headers={"Authorization": f"Bearer {tok}"})
            if r.status_code // 100 != 2:
                return None
            res = r.json().get("result")
            try:
                return int(str(res))
            except Exception:
                return None
    except Exception:
        return None

def _ensure_progress_dir():
    try:
        Path(PROGRESS_FILE).parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
_ensure_progress_dir()
# === end compat shims ===
