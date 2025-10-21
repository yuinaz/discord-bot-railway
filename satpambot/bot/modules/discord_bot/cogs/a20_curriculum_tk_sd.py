import os, json, asyncio, logging
from typing import Dict, Tuple
from datetime import datetime, timezone

import discord
from discord.ext import commands, tasks

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

# === Compatibility shim for a24_curriculum_auto_pin ===
def _load_cfg():
    """Return a dict containing config; at least 'report_channel_id' key for a24."""
    cid = None
    try:
        cid = int(os.getenv("LEINA_CURRICULUM_CHANNEL_ID","") or "0") or None
    except Exception:
        cid = None
    return {"report_channel_id": cid}

class CurriculumTKSD(commands.Cog):
    """Robust TK/SD curriculum cog that reads from Upstash and never crashes."""
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
        else:
            log.info("[a20_curriculum_tk_sd] passive mode (no channel or upstash not enabled)")

    def cog_unload(self):
        try:
            self.loop.cancel()
        except Exception:
            pass

    async def _read_state(self) -> Tuple[str, float]:
        """Return (label, percent) using Upstash junior total; fallback safe defaults."""
        total = 0
        if self.client.enabled:
            try:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    raw = await self.client.get(session, "xp:bot:junior_total")
                    if raw is not None:
                        try:
                            total = int(raw)
                        except Exception:
                            try:
                                j = json.loads(raw)
                                total = int(j.get("overall", 0))
                            except Exception:
                                total = 0
            except Exception as e:
                log.debug("[a20] upstash read failed: %s", e)
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
            if not ch:
                return
            label, pct = await self._read_state()
            text = self.template.format(label=label, percent=pct)
            if text == self._last_text:
                return
            await ch.send(text)
            self._last_text = text
        except Exception as e:
            log.debug("[a20] loop skipped: %s", e)

    @loop.before_loop
    async def _before(self):
        await self.bot.wait_until_ready()

    @commands.command(name="kurjunior")
    async def cmd_kurjunior(self, ctx: commands.Context):
        """Show TK/SD curriculum progress (junior)."""
        label, pct = await self._read_state()
        await ctx.send(self.template.format(label=label, percent=pct))

async def setup(bot: commands.Bot):
    await bot.add_cog(CurriculumTKSD(bot))
