"""
Final Focus Router Guard (v8)
- Catches Forbidden (50013) & re-routes the message to the focus log channel.
- Idempotent install, minimal logging.
"""
from __future__ import annotations

import logging
import os

import discord
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

async def _fallback_to_focus(self, *args, **kwargs):
    focus_id = _int_env("LOG_CHANNEL_ID")
    try:
        bot = kwargs.pop("_bot", None) or getattr(self, "_state", None) and getattr(getattr(self, "_state", None), "client", None)
        if not bot or not focus_id:
            raise RuntimeError("no bot or focus id")
        for g in bot.guilds:
            ch = g.get_channel(focus_id) or await bot.fetch_channel(focus_id)
            if ch:
                return await _ORIG_SEND(ch, *args, **kwargs)
    except Exception as e:
        log.debug("[focus_final] hard fallback failed: %r", e)
    # give up silently
    return

async def _patched_send(self, *args, **kwargs):
    try:
        return await _ORIG_SEND(self, *args, **kwargs)
    except discord.Forbidden as e:
        # Missing permission at destination -> route to focus instead of exploding
        if getattr(e, "status", None) == 403:
            return await _fallback_to_focus(self, *args, **kwargs)
        raise
    except Exception:
        raise

async def setup(bot: commands.Bot):
    global _ORIG_SEND, _INSTALLED
    if _INSTALLED:
        return
    _ORIG_SEND = Messageable.send
    if getattr(Messageable.send, "__name__", "") != "_patched_send":
        Messageable.send = _patched_send  # type: ignore
    _INSTALLED = True
    log.debug("[focus_log_router_final] installed (v8)")
