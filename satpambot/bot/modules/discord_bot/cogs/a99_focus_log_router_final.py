# satpambot/bot/modules/discord_bot/cogs/a99_focus_log_router_final.py
import logging
import os
import re
from typing import Optional

import discord

try:
    # opsional, kalau modul ada
    from satpambot.config.compat_conf import get_conf  # type: ignore
except Exception:  # pragma: no cover
    def get_conf(key: str, default=None):
        return os.getenv(key, default)

log = logging.getLogger(__name__)

# ---------- util ----------
def _get_log_channel_id() -> Optional[int]:
    raw = os.getenv("LOG_CHANNEL_ID") or get_conf("LOG_CHANNEL_ID", "")
    try:
        return int(str(raw).strip())
    except Exception:
        return None

_THREAD_MAP = [
    # (regex title/embed marker, target thread name)
    (re.compile(r"NEURO[- ]LITE GATE STATUS", re.I), "neuro-lite progress"),
    (re.compile(r"SatpamBot Status", re.I), "log restart github"),
    (re.compile(r"SATPAMBOT_PHASH_DB_V1", re.I), "imagephising"),
]

def _guess_thread_name_from_embed(msg_args, msg_kwargs) -> Optional[str]:
    embed = None
    if "embed" in msg_kwargs and isinstance(msg_kwargs["embed"], discord.Embed):
        embed = msg_kwargs["embed"]
    elif msg_args and isinstance(msg_args[0], discord.Embed):
        embed = msg_args[0]
    if not embed:
        return None
    title = (embed.title or "") + " " + (embed.description or "")
    for rx, tname in _THREAD_MAP:
        if rx.search(title):
            return tname
    return None

async def _ensure_thread(channel: discord.TextChannel, name: str):
    # Cari thread dengan nama tsb; kalau ada pakai yang ada.
    for th in channel.threads:
        if th.name == name:
            return th
    # fetch archived threads juga kalau perlu
    async for th in channel.archived_threads(limit=50):
        if th.name == name:
            return th
    # buat baru kalau bener-bener belum ada
    return await channel.create_thread(name=name, type=discord.ChannelType.public_thread)

# ---------- patch ----------
def _install_focus_router():
    """
    Patch Messageable.send supaya SEMUA kiriman diarahkan ke LOG_CHANNEL_ID
    dan, kalau perlu, ke thread yang benar. Idempotent & aman untuk smoketest.
    """
    Messageable = discord.abc.Messageable

    if getattr(Messageable, "_focus_router_v5_installed", False):
        return  # sudah terpasang

    orig_send = Messageable.send

    async def routed_send(self, *args, **kwargs):
        try:
            log_channel_id = _get_log_channel_id()
            if not log_channel_id:
                return await orig_send(self, *args, **kwargs)

            # resolve log channel dari bot yang melekat pada konteks channel
            bot = getattr(self, "_state", None) and getattr(self._state, "client", None)
            if bot is None or not hasattr(bot, "get_channel"):
                return await orig_send(self, *args, **kwargs)

            target = bot.get_channel(log_channel_id)
            if not isinstance(target, discord.TextChannel):
                return await orig_send(self, *args, **kwargs)

            # kalau pesan punya embed tertentu, route ke thread-nya
            tname = _guess_thread_name_from_embed(args, kwargs)
            if tname:
                try:
                    thread = await _ensure_thread(target, tname)
                    return await orig_send(thread, *args, **kwargs)
                except Exception as e:
                    log.warning("[focus_router] thread route fail (%s); fallback to channel", e)

            # default: kirim ke channel log
            return await orig_send(target, *args, **kwargs)
        except Exception as e:
            log.exception("[focus_router] error; fallback passthrough: %s", e)
            return await orig_send(self, *args, **kwargs)

    Messageable._focus_router_v5_installed = True  # type: ignore[attr-defined]
    Messageable._focus_router_v5_orig_send = orig_send  # type: ignore[attr-defined]
    Messageable.send = routed_send  # type: ignore[assignment]
    log.info("[focus_log_router_final] installed")

def setup(bot):
    """
    Dipanggil oleh loader. Jangan pakai @bot.event supaya kompatibel dengan DummyBot di smoketest.
    """
    _install_focus_router()

    # Kalau di runtime discord.py (bukan DummyBot), pasang ulang saat on_ready
    if hasattr(bot, "event"):
        @bot.event  # type: ignore[misc]
        async def on_ready():
            try:
                _install_focus_router()
            except Exception as e:  # pragma: no cover
                log.warning("[focus_log_router_final] re-install on_ready failed: %s", e)
