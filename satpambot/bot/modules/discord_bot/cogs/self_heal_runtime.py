# -*- coding: utf-8 -*-
"""
SelfHealRuntime (Groq-based):
- Summarize errors using Groq client when available (from secrets/local)
- Fails gracefully if key/client missing
"""
from __future__ import annotations
import logging, traceback
from discord.ext import commands
from typing import List, Dict

from satpambot.ai.groq_client import make_groq_client, GroqLLM

log = logging.getLogger(__name__)

SYS = "Kamu asisten devops. Ringkas error (max 5 poin) dan saran perbaikan singkat."
USR = "Ringkas error berikut dan berikan solusi cepat: \\n\\n{err}"

def _build_messages(err_text: str) -> List[Dict]:
    return [
        {"role": "system", "content": SYS},
        {"role": "user", "content": USR.format(err=err_text[:4000])},
    ]

class SelfHealRuntime(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        log.warning("[self-heal] SelfHealRuntime aktif (Groq)")

    async def _maybe_summarize(self, err_text: str):
        try:
            client = GroqLLM(make_groq_client())
        except Exception:
            # no key / client not available
            return
        try:
            summary = client.complete(_build_messages(err_text))
            if summary:
                log.error("[self-heal] Summary:\n%s", summary)
        except Exception:
            log.exception("[self-heal] summarize failed")

    @commands.Cog.listener()
    async def on_error(self, event_method, *args, **kwargs):
        err_text = "".join(traceback.format_exc())
        await self._maybe_summarize(err_text)

async def setup(bot: commands.Bot):
    await bot.add_cog(SelfHealRuntime(bot))
