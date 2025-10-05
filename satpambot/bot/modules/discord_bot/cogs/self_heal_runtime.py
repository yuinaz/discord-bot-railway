
# -*- coding: utf-8 -*-
"""Self-healing runtime (Free Plan friendly)
-------------------------------------------------
- Menahan error agar bot tidak crash/restart.
- Mendeteksi error berulang dan menurunkan beban (degrade) sementara.
- Antri ulang attachment gagal untuk diproses ulang.
- Rate-limited & coalesced logging supaya hemat log Render.
- Tanpa ubah config apa pun; cukup load sebagai cog.
"""
from __future__ import annotations

import asyncio
import logging
import time
from collections import OrderedDict, defaultdict
from typing import Awaitable, Callable, Dict, Tuple

import discord
from discord.ext import commands, tasks

log = logging.getLogger(__name__)

class LRUCache(OrderedDict):
    def __init__(self, maxsize: int = 256):
        super().__init__()
        self.maxsize = maxsize
    def getset(self, k, v):
        if k in self:
            self.move_to_end(k)
        self[k] = v
        if len(self) > self.maxsize:
            self.popitem(last=False)
        return v

_RECENT_ERR = LRUCache(maxsize=256)
def log_once(level_fn: Callable[[str], None], key: str, window_sec: int, msg: str):
    now = time.time()
    last = _RECENT_ERR.get(key, 0)
    if now - last >= window_sec:
        _RECENT_ERR.getset(key, now)
        try:
            level_fn(msg)
        except Exception:
            pass

def now() -> float:
    return time.time()

class SelfHealRuntime(commands.Cog):
    NAME_HINTS = (
        "AntiImagePhashRuntime",
        "AntiImagePhashRuntimeStrict",
        "AntiImagePhishAdvanced",
        "AntiImagePhishSignature",
        "ImagePhishRefIndexer",
        "PhishHashInbox",
        "OCRGuard",
        "FirstTouchAutoBanPackMime",
    )

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._degraded_until: Dict[str, float] = defaultdict(float)
        self._orig_callables: Dict[Tuple[str, str], Callable[..., Awaitable]] = {}
        self._requeue: asyncio.Queue = asyncio.Queue(maxsize=200)
        self._reprocess_loop.start()

    def cog_unload(self):
        try:
            self._reprocess_loop.cancel()
        except Exception:
            pass

    def _is_degraded(self, key: str) -> bool:
        return now() < self._degraded_until.get(key, 0.0)

    def _degrade(self, key: str, seconds: int = 120):
        until = now() + max(10, seconds)
        prev = self._degraded_until.get(key, 0.0)
        if until > prev:
            self._degraded_until[key] = until

    def _wrap_callable(self, cog: commands.Cog, attr: str):
        qual = f"{cog.__class__.__name__}.{attr}"
        if (qual, attr) in self._orig_callables:
            return
        func = getattr(cog, attr)
        if not asyncio.iscoroutinefunction(func):
            return

        async def wrapper(*args, **kwargs):
            key = qual
            if self._is_degraded(key):
                log_once(log.warning, f"degraded:{key}", 60, f"[self-heal] Degraded: skip heavy call {key}")
                return None
            try:
                return await func(*args, **kwargs)
            except Exception as e:  # noqa: BLE001
                self._degrade(key, seconds=180)
                log_once(log.warning, f"err:{key}", 60, f"[self-heal] Suppressed error in {key}: {e!r}")
                try:
                    msg = None
                    for a in args:
                        if isinstance(a, discord.Message):
                            msg = a; break
                    if msg and msg.attachments:
                        url = msg.attachments[0].url
                        await self._safe_put_requeue(msg.guild.id if msg.guild else 0, msg.channel.id, msg.id, url, key)
                except Exception:
                    pass
                return None
        self._orig_callables[(qual, attr)] = func
        setattr(cog, attr, wrapper)

    async def _safe_put_requeue(self, guild_id: int, channel_id: int, message_id: int, url: str, key: str):
        item = (str(guild_id), str(channel_id), str(message_id), url, key)
        try:
            self._requeue.put_nowait(item)
        except asyncio.QueueFull:
            log_once(log.warning, "requeue_full", 300, "[self-heal] requeue full; dropping")

    def _patch_targets(self):
        for name, cog in (self.bot.cogs or {}).items():
            for hint in self.NAME_HINTS:
                if hint in name or name == hint:
                    for attr in ("on_message", "scan_message", "_scan_message",
                                 "process_attachment", "_process_attachment",
                                 "handle_message", "process", "_process"):
                        if hasattr(cog, attr):
                            self._wrap_callable(cog, attr)

    @tasks.loop(seconds=15.0)
    async def _reprocess_loop(self):
        try:
            try:
                item = await asyncio.wait_for(self._requeue.get(), timeout=0.1)
            except asyncio.TimeoutError:
                return
            if not item:
                return
            guild_id, channel_id, message_id, url, key = item
            log_once(log.info, f"requeue:{key}", 300, f"[self-heal] Reprocessing queued item from {key}")
            try:
                ch = self.bot.get_channel(int(channel_id))
                if isinstance(ch, (discord.TextChannel, discord.Thread)):
                    msg = await ch.fetch_message(int(message_id))
                    for cog in list(self.bot.cogs.values()):
                        h = getattr(cog, "on_message", None)
                        if h and asyncio.iscoroutinefunction(h):
                            try:
                                await h(msg)
                            except Exception:
                                pass
            except Exception:
                pass
        except Exception:
            pass

    @_reprocess_loop.before_loop
    async def _wait_ready(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(2.0)
        self._patch_targets()
        log.info("[self-heal] runtime armed")

async def setup(bot: commands.Bot):
    await bot.add_cog(SelfHealRuntime(bot))

def setup_legacy(bot: commands.Bot):
    try:
        bot.loop.create_task(setup(bot))
    except Exception:
        pass
