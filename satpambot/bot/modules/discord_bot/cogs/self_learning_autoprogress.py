# satpambot/bot/modules/discord_bot/cogs/self_learning_autoprogress.py
from __future__ import annotations

import contextlib
import datetime as dt
import json
import logging
from pathlib import Path
from statistics import mean
from typing import Deque, Optional
from collections import deque

import discord
from discord.ext import commands, tasks

from satpambot.shared.lingua_id_slang import score_indonesian_coverage, is_mostly_indonesian
from satpambot.shared.progress_gate import ProgressGate, Phase

log = logging.getLogger(__name__)

STORE_STATS = Path("data/sl_autoprogress.json")
STORE_GATE = Path("data/progress_gate.json")

# Tunables — start conservative to avoid premature unlock
MIN_SEEN_TK = 800         # messages observed for TK
MIN_SEEN_SD = 1800        # additional observed for SD total
ROLL_TK = 250             # rolling window for TK
ROLL_SD = 500             # rolling window for SD

# Quality thresholds (heavily weight Indonesian comprehension)
TK_MIN_AVG = 0.62         # rolling avg (slang+func coverage weighted) for TK
SD_MIN_AVG = 0.75         # stricter for SD

# Stability: need several consecutive epochs passing before bumping to 100
NEED_STABLE_TICKS = 6     # each tick ~5m => ~30m of stability

TICK_MINUTES = 5.0

def _now_id() -> dt.datetime:
    try:
        import zoneinfo
        tz = zoneinfo.ZoneInfo("Asia/Jakarta")
    except Exception:
        tz = dt.timezone(dt.timedelta(hours=7))
    return dt.datetime.now(tz=tz)


class _Stats:
    def __init__(self):
        self.seen: int = 0
        self.roll_cov: Deque[float] = deque(maxlen=max(ROLL_SD, ROLL_TK))  # coverage scores
        self.stable_pass: int = 0

    def to_dict(self):
        return {"seen": self.seen, "roll_cov": list(self.roll_cov), "stable_pass": self.stable_pass}

    @classmethod
    def from_file(cls, p: Path) -> "_Stats":
        s = cls()
        if p.exists():
            with contextlib.suppress(Exception):
                d = json.loads(p.read_text(encoding="utf-8"))
                s.seen = int(d.get("seen", 0))
                s.roll_cov = deque([float(x) for x in d.get("roll_cov", [])], maxlen=max(ROLL_SD, ROLL_TK))
                s.stable_pass = int(d.get("stable_pass", 0))
        return s

    def save(self, p: Path):
        p.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    def coverage_avg(self, last_n: int) -> float:
        if not self.roll_cov:
            return 0.0
        if last_n <= 0:
            return mean(self.roll_cov) if self.roll_cov else 0.0
        return mean(list(self.roll_cov)[-last_n:])


class SelfLearningAutoProgress(commands.Cog):
    """Observe public human messages in Indonesian variety; compute comprehension coverage.
    Update TK/SD progress **automatically**; no manual commands needed.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.stats = _Stats.from_file(STORE_STATS)
        self.gate = ProgressGate(STORE_GATE)
        self._last_tick: Optional[dt.datetime] = None
        self._tick.start()

    def cog_unload(self):
        with contextlib.suppress(Exception):
            self._tick.cancel()

    @tasks.loop(minutes=TICK_MINUTES)
    async def _tick(self):
        # Called periodically to re-evaluate progress and possibly bump TK/SD %
        # Compute rolling averages
        tk_avg = self.stats.coverage_avg(ROLL_TK)
        sd_avg = self.stats.coverage_avg(ROLL_SD)

        s = self.gate.state()
        tk_pct = int(min(100, round(100 * min(1.0, (self.stats.seen / max(1, MIN_SEEN_TK)) * (tk_avg / max(1e-6, TK_MIN_AVG))))))
        sd_pct = int(min(100, round(100 * min(1.0, (self.stats.seen / max(1, MIN_SEEN_SD)) * (sd_avg / max(1e-6, SD_MIN_AVG))))))

        # Stability gate: to mark full completion we ensure several consecutive passes
        passes = (
            (self.stats.seen >= MIN_SEEN_TK and tk_avg >= TK_MIN_AVG) and
            (self.stats.seen >= MIN_SEEN_SD and sd_avg >= SD_MIN_AVG)
        )
        if passes:
            self.stats.stable_pass += 1
        else:
            self.stats.stable_pass = 0

        if self.stats.stable_pass >= NEED_STABLE_TICKS:
            tk_pct = 100
            sd_pct = 100

        self.gate.set_phase_value(tk=tk_pct, sd=sd_pct)
        self.stats.save(STORE_STATS)

    @_tick.before_loop
    async def _before_tick(self):
        await self.bot.wait_until_ready()

    @commands.Cog.listener("on_message")
    async def _observe(self, message: discord.Message):
        # Only observe human messages in guild channels. Do nothing in DM.
        if not message or message.author.bot or message.guild is None:
            return
        # Sample text
        text = f"{message.author.display_name}: {message.content or ''}"
        slang, func = score_indonesian_coverage(text)
        cov = slang * 0.65 + func * 0.35  # weight slang slightly higher for Indonesian internet chats
        self.stats.seen += 1
        self.stats.roll_cov.append(cov)
        # Persist lazily
        if self.stats.seen % 50 == 0:
            self.stats.save(STORE_STATS)


async def setup(bot: commands.Bot):
    await bot.add_cog(SelfLearningAutoProgress(bot))
