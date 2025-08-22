
# -*- coding: utf-8 -*-
"""
Enhanced live metrics push:
- Accurate member & online counts with safe fallbacks.
- Uses cache first (fast), then REST approximate counts when needed.
- Optional guild chunking on startup (if privileged intents enabled).
"""
from __future__ import annotations

import math
import time
import asyncio
from typing import Dict, Tuple

import discord
from discord.ext import commands, tasks

try:
    from satpambot.dashboard.live_store import set_stats  # type: ignore
except Exception:  # pragma: no cover
    def set_stats(d: Dict[str, int]) -> None:
        globals()["_STORE"] = d


def _latency_ms(bot: commands.Bot) -> int:
    try:
        val = float(getattr(bot, "latency", 0.0) or 0.0)
    except Exception:
        return 0
    if not math.isfinite(val) or val < 0:
        return 0
    return int(val * 1000.0)


def _cache_counts(bot: commands.Bot) -> Tuple[int, int]:
    """Return (members, online) from cache only (no REST)."""
    total_members = 0
    total_online = 0
    for g in list(bot.guilds):
        mc = getattr(g, "member_count", None)
        if isinstance(mc, int):
            total_members += max(0, mc)
        # presence (requires presences intent + chunked)
        try:
            online = sum(1 for m in g.members if getattr(m, "status", discord.Status.offline) != discord.Status.offline)
            total_online += online
        except Exception:
            pass
    return total_members, total_online


async def _rest_counts(bot: commands.Bot) -> Tuple[int, int]:
    """Return (members, online) using REST approximate counts (lightweight)."""
    total_members = 0
    total_online = 0
    for g in list(bot.guilds):
        try:
            fg = await bot.fetch_guild(g.id, with_counts=True)
            # discord.py exposes these two attributes when with_counts=True
            total_members += int(getattr(fg, "approximate_member_count", 0) or 0)
            total_online += int(getattr(fg, "approximate_presence_count", 0) or 0)
        except Exception:
            # best effort, keep going
            pass
        await asyncio.sleep(0)  # yield
    return total_members, total_online


async def _maybe_chunk_guilds(bot: commands.Bot, timeout_per_guild: float = 8.0) -> None:
    """Optionally chunk guild members to populate cache (no-op if not allowed)."""
    # Only run once per process; store a flag on bot.
    if getattr(bot, "_satpam_chunk_done", False):
        return
    setattr(bot, "_satpam_chunk_done", True)

    for g in list(bot.guilds):
        try:
            await asyncio.wait_for(g.chunk(cache=True), timeout=timeout_per_guild)
        except Exception:
            pass
        await asyncio.sleep(0)


async def build_snapshot(bot: commands.Bot, *, enable_rest_fallback: bool = True) -> Dict[str, int]:
    # basic counts always cheap
    guilds = len(bot.guilds)
    try:
        channels = sum(len(g.channels) for g in bot.guilds)
    except Exception:
        channels = 0
    try:
        threads = sum(len(getattr(g, "threads", [])) for g in bot.guilds)
    except Exception:
        threads = 0

    members, online = _cache_counts(bot)

    # REST fallback if cache looks empty (or nearly empty)
    if enable_rest_fallback and (members == 0 or online == 0):
        rmembers, ronline = await _rest_counts(bot)
        # prefer REST if it's larger (likely more accurate)
        members = max(members, rmembers)
        online  = max(online, ronline)

    return dict(
        guilds=guilds,
        members=members,
        online=online,
        channels=channels,
        threads=threads,
        latency_ms=_latency_ms(bot),
        updated=int(time.time()),
    )


class LiveMetricsPush(commands.Cog):
    """Background task to periodically push live stats to web dashboard."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._last_rest = 0.0  # throttle REST usage
        self._loop.start()

    @tasks.loop(seconds=5.0)
    async def _loop(self) -> None:
        try:
            # throttle REST fallback: at most once per 60s
            now = time.time()
            enable_rest = now - self._last_rest >= 60.0
            snap = await build_snapshot(self.bot, enable_rest_fallback=enable_rest)
            if enable_rest and (snap.get("members", 0) > 0 or snap.get("online", 0) > 0):
                self._last_rest = now
            set_stats(snap)
        except Exception as exc:
            print(f"[live_metrics_push] WARN: {exc!r}")

    @_loop.before_loop
    async def _before(self) -> None:
        await self.bot.wait_until_ready()
        # Try chunking once at startup (fast if already chunked / not allowed)
        try:
            await _maybe_chunk_guilds(self.bot)
        except Exception:
            pass

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(LiveMetricsPush(bot))
