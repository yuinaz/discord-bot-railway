"""
Shadow Public Silencer (v8)
- If message destination is NOT the focus channel/thread, block quietly.
- Logging downgraded to DEBUG unless SILENCER_LOG_BLOCKED=1
- Always allow the focus channel id.
"""
from __future__ import annotations

import logging
import os
from discord.abc import Messageable
from discord.ext import commands

log = logging.getLogger(__name__)
_ORIG_SEND = None
_INSTALLED = False

def _int_env(name: str):
    v = os.getenv(name, "").strip()
    if not v:
        return None
    try:
        return int(v)
    except ValueError:
        return None

def _should_log() -> bool:
    return os.getenv("SILENCER_LOG_BLOCKED", "0") == "1"

async def _patched_send(self, *args, **kwargs):
    focus_id = _int_env("LOG_CHANNEL_ID")
    try:
        ch = getattr(self, "channel", self)
        dest_id = getattr(ch, "id", None)
        if focus_id and dest_id == focus_id:
            return await _ORIG_SEND(self, *args, **kwargs)

        # Quiet drop (router will reroute earlier anyway).
        if _should_log():
            log.info("[shadow_silencer] blocked send to %s (id=%s)", getattr(ch, "name", "?"), dest_id)
        else:
            log.debug("[shadow_silencer] blocked send to id=%s", dest_id)
        return
    except Exception:
        # never explode
        return

async def setup(bot: commands.Bot):
    """Install very early in the pipeline; other routers may reroute before us."""
    global _ORIG_SEND, _INSTALLED
    if _INSTALLED:
        return
    _ORIG_SEND = Messageable.send
    Messageable.send = _patched_send  # type: ignore
    _INSTALLED = True
    log.debug("[shadow_silencer] active (public allowed? False)")
