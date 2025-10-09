
# -*- coding: utf-8 -*-
"""ShadowPublicSilencer (smoke-safe)
Menjaga bot **silent di public** sampai gate mengizinkan.
- Mengizinkan: DM, #log-botphising, thread "neuro-lite progress", dan channel mod-command.
- Mendengarkan event `learning_gate_update(allow, state)` dari LearningPromotionGate.
- ENV `SHADOW_PUBLIC_FORCE` (default 1) menahan shadow saat awal.
- **Hotfix:** Tidak lagi memakai `bot.loop.create_task` (kompatibel DummyBot di smoke test).
"""
from __future__ import annotations
import os, logging, asyncio
from typing import Set

import discord
from discord.ext import commands
import discord.abc as abc

from satpambot.bot.modules.discord_bot.helpers.thread_utils import ensure_neuro_thread, find_log_channel, DEFAULT_THREAD_NAME

log = logging.getLogger(__name__)

_ALLOW_PUBLIC: bool = False  # updated by gate event / env
_READY: bool = False
_WHITELIST_IDS: Set[int] = set()

def _env_force_shadow_default() -> bool:
    raw = os.getenv("SHADOW_PUBLIC_FORCE", "1")
    return raw not in ("0","false","False","no","No")

def _is_dm_channel(obj) -> bool:
    return getattr(obj, "guild", None) is None

async def _calc_whitelist(bot: commands.Bot) -> None:
    global _WHITELIST_IDS
    _WHITELIST_IDS.clear()
    try:
        ch = await find_log_channel(bot)
        if ch:
            _WHITELIST_IDS.add(int(ch.id))
    except Exception:
        pass
    try:
        th = await ensure_neuro_thread(bot, DEFAULT_THREAD_NAME)
        if th:
            _WHITELIST_IDS.add(int(th.id))
    except Exception:
        pass
    # Optional: allow 'mod-command' by name
    try:
        for g in getattr(bot, "guilds", []):
            for t in getattr(g, "text_channels", []):
                if getattr(t, "name", "") == "mod-command":
                    _WHITELIST_IDS.add(int(t.id))
    except Exception:
        pass
    log.info("[shadow_silencer] whitelist ids set: %s", list(_WHITELIST_IDS))

async def _gated_send(original_send, self, *args, **kwargs):
    # If DM, always allow.
    if _is_dm_channel(self):
        return await original_send(self, *args, **kwargs)
    # If not ready yet, respect env default
    allow_public = _ALLOW_PUBLIC if _READY else (not _env_force_shadow_default())
    ch_id = int(getattr(self, "id", 0) or 0)
    if allow_public or ch_id in _WHITELIST_IDS:
        return await original_send(self, *args, **kwargs)
    # Shadow: drop silently (no-op) but log debug
    content = kwargs.get("content", None)
    if not content and args and isinstance(args[0], str):
        content = args[0]
    try:
        preview = (content[:120] + "…") if isinstance(content, str) and len(content) > 120 else content
        log.debug("[shadow_silencer] drop public send to %s (content=%r)", ch_id, preview)
    except Exception:
        pass
    return None

class ShadowPublicSilencer(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._install_send_wrapper()
        # Jangan pakai bot.loop — gunakan cog_load untuk menjadwalkan task

    async def cog_load(self) -> None:
        # Dipanggil setelah cog ditambahkan — aman untuk menjadwalkan task
        try:
            asyncio.create_task(self._post_ready())
        except Exception:
            # fallback synchronous init (smoke env)
            await self._post_ready()

    async def _post_ready(self):
        global _READY, _ALLOW_PUBLIC
        wait = getattr(self.bot, "wait_until_ready", None)
        if callable(wait):
            try:
                await wait()
            except Exception:
                pass
        try:
            await _calc_whitelist(self.bot)
        finally:
            _ALLOW_PUBLIC = False  # default shadow on boot
            _READY = True
            log.info("[shadow_silencer] active (public allowed? %s)", _ALLOW_PUBLIC)

    def _install_send_wrapper(self):
        original_send = abc.Messageable.send
        async def wrapper(this, *a, **kw):
            return await _gated_send(original_send, this, *a, **kw)
        if getattr(abc.Messageable.send, "__name__", "") != "wrapper":
            abc.Messageable.send = wrapper
            log.info("[shadow_silencer] Messageable.send patched")

    @commands.Cog.listener("on_learning_gate_update")
    async def _on_gate_update(self, allow: bool, state: dict):
        global _ALLOW_PUBLIC
        _ALLOW_PUBLIC = bool(allow)
        log.info("[shadow_silencer] gate update: allow_public=%s state=%s", _ALLOW_PUBLIC, {k: state.get(k) for k in ("junior_percent","senior_percent")})

async def setup(bot: commands.Bot):
    await bot.add_cog(ShadowPublicSilencer(bot))
