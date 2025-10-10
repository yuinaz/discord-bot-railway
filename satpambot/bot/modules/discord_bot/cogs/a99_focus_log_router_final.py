# -*- coding: utf-8 -*-
# Final hard router — force all sends into LOG_CHANNEL_ID (+thread),
# keep re-installing so we stay on top of any other monkey patches,
# block "rules" channel outright, and de-dup spammy embeds.
import asyncio
import json
import logging
import os
import re
import time
from typing import Optional, Dict, Tuple

import discord

log = logging.getLogger(__name__)

# ---------- config helpers ----------
def _get_conf(key: str, default=None):
    # env first, fallback to optional compat_conf if present
    val = os.getenv(key, default)
    if val is not None:
        return val
    try:
        from satpambot.config.compat_conf import get_conf as _gc  # type: ignore
        return _gc(key, default)
    except Exception:
        return default

def _log_channel_id() -> Optional[int]:
    raw = _get_conf("LOG_CHANNEL_ID", "")
    try:
        return int(str(raw).strip())
    except Exception:
        return None

# Channel name denylist (lowercased compare)
_DENY_NAMES = {"⛔︲rules", "rules", "rule", "📜︲rules"}

# Thread routing by embed title/desc marker
_THREAD_MAP: Tuple[Tuple[re.Pattern, str], ...] = (
    (re.compile(r"NEURO[- ]?LITE GATE STATUS", re.I), "neuro-lite progress"),
    (re.compile(r"SATPAMBOT_PHASH_DB_V1", re.I), "imagephising"),
    (re.compile(r"SatpamBot Status", re.I), "log restart github"),
    (re.compile(r"\bML[- ]?STATE\b", re.I), "ml-state"),
)

# spam control: remember last message per thread + fingerprint
_last_fp: Dict[str, Tuple[str, float, discord.Message]] = {}

def _embed_from_args(args, kwargs) -> Optional[discord.Embed]:
    e = kwargs.get("embed")
    if isinstance(e, discord.Embed):
        return e
    if args and isinstance(args[0], discord.Embed):
        return args[0]
    return None

def _guess_thread(embed: Optional[discord.Embed]) -> Optional[str]:
    if not embed:
        return None
    title = (embed.title or "") + " " + (embed.description or "")
    for rx, name in _THREAD_MAP:
        if rx.search(title):
            return name
    return None

async def _ensure_thread(ch: discord.TextChannel, name: str) -> discord.abc.Messageable:
    # search open threads first
    for th in ch.threads:
        if th.name == name:
            return th
    # then archived (first few pages)
    try:
        async for th in ch.archived_threads(limit=100):
            if th.name == name:
                return th
    except Exception:
        pass
    # create if not found
    return await ch.create_thread(name=name, type=discord.ChannelType.public_thread)

def _fingerprint_embed(embed: discord.Embed) -> str:
    # robust-ish: title/desc/fields only
    d = embed.to_dict()
    d = {k: d.get(k) for k in ("title", "description", "fields", "footer")}
    return json.dumps(d, sort_keys=True, ensure_ascii=False)

# ---------- installer ----------
_SIGNATURE = "focus_router_v6"

def _is_installed() -> bool:
    return getattr(discord.abc.Messageable, "_focus_router_signature", "") == _SIGNATURE

def _install(force: bool = False):
    Messageable = discord.abc.Messageable
    if _is_installed() and not force:
        return

    orig_send = getattr(Messageable, "_focus_router_orig_send", None) or Messageable.send

    async def routed_send(self, *args, **kwargs):
        # short-circuit deny: never touch rules-like channels
        try:
            # Resolve bot & target log channel
            bot = getattr(self, "_state", None) and getattr(self._state, "client", None)
            log_id = _log_channel_id()
            if not bot or not log_id:
                return await orig_send(self, *args, **kwargs)

            target = bot.get_channel(log_id)
            if not isinstance(target, discord.TextChannel):
                return await orig_send(self, *args, **kwargs)

            # If current target looks like "rules" or not the log channel, reroute.
            try:
                ch_name = (getattr(self, "name", "") or "").lower()
            except Exception:
                ch_name = ""

            # always reroute if not the log channel
            must_route = True
            if hasattr(self, "id"):
                try:
                    must_route = (self.id != log_id)
                except Exception:
                    must_route = True

            if ch_name in _DENY_NAMES:
                must_route = True

            dest: discord.abc.Messageable = target

            # Thread mapping if embed matches
            embed = _embed_from_args(args, kwargs)
            tname = _guess_thread(embed) if embed else None
            if tname:
                try:
                    dest = await _ensure_thread(target, tname)
                except Exception as e:
                    log.warning("[focus_final] ensure_thread failed (%s); fallback to channel", e)
                    dest = target

            # Anti-spam for embeds: if same payload to same thread within 90s → return last message
            if embed and isinstance(dest, (discord.Thread, discord.TextChannel)):
                lane = target.name if isinstance(dest, discord.TextChannel) else dest.name
                fp = _fingerprint_embed(embed)
                now = time.time()
                prev = _last_fp.get(lane)
                if prev and prev[0] == fp and (now - prev[1]) < float(_get_conf("FOCUS_DEDUP_WINDOW_SEC", "90")):
                    # return last message without sending new one
                    return prev[2]

            # finally send to the chosen destination
            msg = await orig_send(dest if must_route else self, *args, **kwargs)

            # save last for anti-spam (embeds only)
            if embed and isinstance(msg, discord.Message):
                lane = target.name if isinstance(dest, discord.TextChannel) else getattr(dest, "name", str(log_id))
                _last_fp[lane] = (_fingerprint_embed(embed), time.time(), msg)

            return msg

        except Exception as e:
            log.exception("[focus_final] routed_send error; passthrough: %s", e)
            return await orig_send(self, *args, **kwargs)

    # mark + install
    Messageable._focus_router_orig_send = orig_send  # type: ignore[attr-defined]
    Messageable.send = routed_send  # type: ignore[assignment]
    Messageable._focus_router_signature = _SIGNATURE  # type: ignore[attr-defined]
    log.info("[focus_log_router_final] installed")

async def _keep_installed_task():
    # keep us on top: re-assert a few times early, lalu periodik
    for _ in range(10):
        await asyncio.sleep(0.8)
        _install(force=True)
    while True:
        await asyncio.sleep(60.0)
        _install(force=True)

def setup(bot):
    _install(force=True)
    # schedule keepalive only when real bot (DummyBot smoketest tidak punya loop)
    if hasattr(bot, "loop"):
        try:
            bot.loop.create_task(_keep_installed_task())
        except Exception:
            # fallback for newer discord.py using asyncio.run
            asyncio.create_task(_keep_installed_task())
