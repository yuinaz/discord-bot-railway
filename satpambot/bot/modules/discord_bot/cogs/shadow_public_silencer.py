# -*- coding: utf-8 -*-
"""shadow_public_silencer.py — Hotfix v3
- Hapus dependency `bot.loop.create_task()` → pakai `asyncio.create_task()` + `cog_load()`.
- Tahan di discord.py 2.x/py-cord/nextcord dan runner smoke (DummyBot) tanpa attribute `loop`.
- Patch `discord.abc.Messageable.send` sekali saja; bisa dinonaktifkan via ENV.
- Whitelist channel/thread id; AMAN untuk thread 'neuro-lite progress' dan DM.
"""
from __future__ import annotations
import os, asyncio, logging, contextlib
from typing import Set, Optional

import discord
from discord.ext import commands
from discord.abc import Messageable

try:
    # optional helper (agar selaras dgn bundle kita)
    from satpambot.bot.modules.discord_bot.helpers.thread_utils import DEFAULT_THREAD_NAME
except Exception:
    DEFAULT_THREAD_NAME = "neuro-lite progress"

log = logging.getLogger(__name__)

_PATCHED = False
_ORIG_SEND = None  # type: ignore

def _parse_ids(s: str) -> Set[int]:
    out: Set[int] = set()
    for part in (s or "").replace(";", ",").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            out.add(int(part))
        except Exception:
            pass
    return out

def _env_bool(name: str, default: bool = False) -> bool:
    v = os.getenv(name, "").strip()
    if not v:
        return default
    return v not in ("0", "false", "False", "no", "No")

def _channel_id_from_env() -> Optional[int]:
    raw = os.getenv("LOG_CHANNEL_ID", "") or os.getenv("SELFHEAL_THREAD_CHANNEL_ID", "")
    try:
        return int(raw.strip()) if raw else None
    except Exception:
        return None

async def _is_neuro_thread(channel: discord.abc.Messageable) -> bool:
    try:
        if isinstance(channel, discord.Thread):
            return (channel.name or "").strip().lower() == (DEFAULT_THREAD_NAME or "").strip().lower()
    except Exception:
        pass
    return False

def _install_send_patch(whitelist_ids: Set[int], public_allowed: bool):
    global _PATCHED, _ORIG_SEND
    if _PATCHED:
        return
    _ORIG_SEND = Messageable.send

    async def _guarded_send(self: Messageable, *args, **kwargs):
        # Always allow if public allowed
        if public_allowed:
            return await _ORIG_SEND(self, *args, **kwargs)

        # DM selalu boleh
        if isinstance(self, (discord.DMChannel, discord.GroupChannel)):
            return await _ORIG_SEND(self, *args, **kwargs)

        # Thread 'neuro-lite progress' selalu boleh
        if await _is_neuro_thread(self):  # type: ignore[arg-type]
            return await _ORIG_SEND(self, *args, **kwargs)

        # Text channel: cek whitelist id
        chan_id = getattr(self, "id", None)
        if isinstance(chan_id, int) and chan_id in whitelist_ids:
            return await _ORIG_SEND(self, *args, **kwargs)

        # Default: blok, log sekali-sekali
        try:
            g = getattr(self, "guild", None)
            gname = getattr(g, "name", "?")
            cname = getattr(self, "name", "?")
            log.info("[shadow_silencer] blocked send to #%s (guild=%s)", cname, gname)
        except Exception:
            log.info("[shadow_silencer] blocked send to a non-whitelisted channel")
        return None

    Messageable.send = _guarded_send  # type: ignore[assignment]
    _PATCHED = True
    log.info("[shadow_silencer] Messageable.send patched")

class ShadowPublicSilencer(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._task = None

    async def cog_load(self):
        # discord.py 2.x friendly
        self._task = asyncio.create_task(self._post_ready())

    def cog_unload(self):
        with contextlib.suppress(Exception):
            if self._task:
                self._task.cancel()

    async def _post_ready(self):
        await self.bot.wait_until_ready()
        # mode: force off public unless explicitly allowed
        public_allowed = _env_bool("SHADOW_PUBLIC_FORCE", False)
        wl = set()
        cid = _channel_id_from_env()
        if cid:
            wl.add(cid)
        wl |= _parse_ids(os.getenv("SHADOW_PUBLIC_WHITELIST_IDS", ""))
        log.info("[shadow_silencer] whitelist ids set: %s", sorted(wl) if wl else [])
        log.info("[shadow_silencer] active (public allowed? %s)", public_allowed)
        _install_send_patch(wl, public_allowed)

async def setup(bot: commands.Bot):
    await bot.add_cog(ShadowPublicSilencer(bot))
