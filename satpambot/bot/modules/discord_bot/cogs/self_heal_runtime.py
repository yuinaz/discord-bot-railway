# -*- coding: utf-8 -*-
"""
SelfHealRuntime (minimal patch):
- Use OpenAI v1 helper if key present
- Keep working even without key (logs only)
"""
from __future__ import annotations
import os, logging, traceback
from discord.ext import commands
from typing import List, Dict

from ..helpers.openai_client import chat_once  # will raise if SDK/key missing

log = logging.getLogger(__name__)

SYS = "Kamu asisten devops. Ringkas error (max 5 poin) dan saran perbaikan singkat."

def _build_messages(err_text: str) -> List[Dict[str, str]]:
    return [
        {"role":"system","content": SYS},
        {"role":"user","content": "Ringkas error berikut (maks 5 poin) dan sarankan perbaikan singkat:\n\n" + err_text}
    ]

class SelfHealRuntime(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        log.warning("[self-heal] SelfHealRuntime aktif")

    async def _maybe_summarize(self, err_text: str):
        try:
            key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI-KEY")
            if not key:
                log.info("[self-heal] OPENAI key not found; skip AI summarize")
                return
            summary = chat_once(_build_messages(err_text), temperature=0.2)
            if summary:
                log.error("[self-heal] Summary:\n%s", summary)
        except Exception:
            log.exception("[self-heal] summarize failed")
