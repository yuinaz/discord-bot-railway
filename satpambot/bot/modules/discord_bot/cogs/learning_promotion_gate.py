# -*- coding: utf-8 -*-
from __future__ import annotations
import os, json, asyncio, logging
from pathlib import Path

import discord
from discord.ext import commands, tasks

from satpambot.bot.modules.discord_bot.helpers.progress_eval import evaluate_progress
from satpambot.bot.modules.discord_bot.helpers.thread_utils import ensure_neuro_thread, DEFAULT_THREAD_NAME
from satpambot.bot.modules.discord_bot.helpers.message_keeper import get_keeper

log = logging.getLogger(__name__)

JUNIOR_JSON = Path("data/learn_progress_junior.json")
SENIOR_JSON = Path("data/learn_progress_senior.json")
PROMOTE_ON_100 = os.getenv("PROMOTE_ON_100", "1") not in ("0","false","False","no","No")
GATE_KEY = "[neuro-lite:gate]"

class LearningPromotionGate(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.state = {"junior_percent": 0.0, "senior_percent": 0.0, "allow_promotion": False}
        self.ensure_once.start()
        self.watch_loop.start()

    def cog_unload(self):
        for t in (self.ensure_once, self.watch_loop):
            try: t.cancel()
            except Exception: pass

    def _render_gate_block(self) -> str:
        jp = self.state.get("junior_percent", 0.0)
        sp = self.state.get("senior_percent", 0.0)
        allow = self.state.get("allow_promotion", False)
        lines = [
            "**NEURO-LITE GATE STATUS**",
            f"- Junior: **{jp:.1f}%**",
            f"- Senior: **{sp:.1f}%**",
            f"- Rule: Junior must be **100%** before Senior unlocks",
            f"- Promotion Allowed: **{'YES' if allow else 'NO'}**",
        ]
        return "\n".join(lines)

    def _recompute(self):
        prog = evaluate_progress(JUNIOR_JSON, SENIOR_JSON)
        allow = bool(PROMOTE_ON_100 and prog["junior_percent"] >= 100.0)
        self.state.update(prog)
        self.state["allow_promotion"] = allow
        try:
            Path("data").mkdir(parents=True, exist_ok=True)
            Path("data/learning_gate_state.json").write_text(json.dumps(self.state, indent=2), encoding="utf-8")
        except Exception:
            pass
        return allow

    async def _publish_gate_status(self):
        th = await ensure_neuro_thread(self.bot, DEFAULT_THREAD_NAME)
        if not th:
            return
        keeper = get_keeper(self.bot)
        try:
            await keeper.update(th, key=GATE_KEY, content=self._render_gate_block())
        except Exception as e:
            log.warning("[learning_promotion_gate] keeper update failed: %s", e)

    def _try_signal_public_gate(self, allow: bool):
        try:
            self.bot.dispatch("learning_gate_update", allow, dict(self.state))
        except Exception:
            pass

    @tasks.loop(count=1)
    async def ensure_once(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(1.0)
        allow = self._recompute()
        await self._publish_gate_status()
        self._try_signal_public_gate(allow)

    @tasks.loop(seconds=90)
    async def watch_loop(self):
        await self.bot.wait_until_ready()
        allow = self._recompute()
        await self._publish_gate_status()
        self._try_signal_public_gate(allow)

    @ensure_once.before_loop
    async def _before(self):
        await self.bot.wait_until_ready()

    @watch_loop.before_loop
    async def _before2(self):
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot):
    await bot.add_cog(LearningPromotionGate(bot))
