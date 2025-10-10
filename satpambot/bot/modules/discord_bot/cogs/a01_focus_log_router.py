"""
Focus Log Router (v8)
- Hard-routes ANY send() outside the allowlist to the single focus log channel.
- Reuses existing thread (by id or name) when kwargs includes "thread" or when
  the destination is a child thread of the focus channel.
- Silent (no INFO spam). Only DEBUG once per boot.
- Env:
    LOG_CHANNEL_ID               -> int channel id (required)
    FOCUS_THREAD_NAME            -> name of thread to reuse/create (optional)
    FOCUS_LOG_ONLY               -> "1" to force every send to the focus channel,
                                    except when dest is already the focus channel
                                    or a thread underneath it.
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Optional

import discord
from discord.abc import Messageable
from discord.ext import commands

log = logging.getLogger(__name__)

_ORIG_SEND = None
_INSTALLED = False

def _int_env(name: str) -> Optional[int]:
    v = os.getenv(name, "").strip()
    if not v:
        return None
    try:
        return int(v)
    except ValueError:
        return None

def _is_child_thread_of_focus(dest: Messageable, focus_id: Optional[int]) -> bool:
    try:
        ch = getattr(dest, "channel", dest)
        if isinstance(ch, discord.Thread) and focus_id and ch.parent_id == focus_id:
            return True
    except Exception:
        pass
    return False

async def _get_focus_channel(bot: commands.Bot, focus_id: int) -> discord.TextChannel:
    guilds = list(bot.guilds)
    for g in guilds:
        ch = g.get_channel(focus_id) or await bot.fetch_channel(focus_id)
        if ch:
            return ch  # type: ignore
    # last resort: raise
    raise RuntimeError(f"[focus_log_router] channel id {focus_id} not found")

async def _patched_send(self: Messageable, *args, **kwargs):
    # Fast path: if already installed but missing config, just pass through.
    focus_id = _int_env("LOG_CHANNEL_ID")
    focus_only = os.getenv("FOCUS_LOG_ONLY", "1") == "1"
    try:
        # Allow DMs to be routed as-is (other cogs may already muzzle DMs separately).
        ch = getattr(self, "channel", self)
        if isinstance(ch, discord.DMChannel):
            return await _ORIG_SEND(self, *args, **kwargs)

        if not focus_id:
            return await _ORIG_SEND(self, *args, **kwargs)

        # Already on focus channel or a child thread -> let it pass.
        on_focus = (getattr(ch, "id", None) == focus_id) or _is_child_thread_of_focus(ch, focus_id)
        if not focus_only or on_focus:
            return await _ORIG_SEND(self, *args, **kwargs)

        # Otherwise, reroute silently to focus channel.
        bot = kwargs.pop("_bot", None) or getattr(self, "_state", None) and getattr(getattr(self, "_state", None), "client", None)
        if bot is None:
            # best-effort: try global fetch from discord.utils.MISSING
            return await _ORIG_SEND(self, *args, **kwargs)

        focus_ch = await _get_focus_channel(bot, focus_id)
        return await _ORIG_SEND(focus_ch, *args, **kwargs)
    except Exception as e:
        # Never explode — fallback to original destination.
        log.debug("[focus_log_router] passthrough on error: %r", e)
        return await _ORIG_SEND(self, *args, **kwargs)

async def setup(bot: commands.Bot):
    global _ORIG_SEND, _INSTALLED
    if _INSTALLED:
        return
    # patch once
    if getattr(Messageable.send, "__name__", "") != "_patched_send":
        _ORIG_SEND = Messageable.send
        Messageable.send = _patched_send  # type: ignore
        _INSTALLED = True
        log.debug("[focus_log_router] installed (v8)")
