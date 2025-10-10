# a01_focus_log_router.py
# Force-route all bot outputs to a single log channel (and its threads),
# and enforce singleton embeds for key keepers so there are no duplicates.
# Load order: early (a01_) so it patches Messageable.send before others.

from __future__ import annotations
import asyncio, json, re, sys, traceback
import discord
from discord.abc import Messageable

try:
    from satpambot.config.compat_conf import get_conf
except Exception:  # fallback if compat_conf not available
    def get_conf():
        import os
        return {k:v for k,v in os.environ.items()}

_ORIG_SEND = Messageable.send

# singleton state
_singletons: dict[str, discord.Message] = {}
_locks: dict[str, asyncio.Lock] = {}

# detect keys & thread target by content/embed
NEURO_KEYS = [
    # (key, regex to detect in content or embed title, thread name)
    ("neuro_gate", re.compile(r"NEURO[- ]LITE GATE STATUS", re.I), "neuro-lite progress"),
    ("status",     re.compile(r"SatpamBot Status", re.I),          "log restart github"),
    ("phash_db",   re.compile(r"SATPAMBOT[_-]PHASH[_-]DB[_-]V1", re.I), "imagephising"),
]

def _json_like(text: str) -> bool:
    t = text.strip()
    return (t.startswith("{") and t.endswith("}")) or t.startswith("```json")

def _extract_key_from_params(content, embed, embeds) -> tuple[str|None, str|None]:
    # returns (key, thread_name) if detected
    all_text = []
    if isinstance(content, str):
        all_text.append(content)
    for e in ([embed] if embed else []) + (embeds or []):
        try:
            if e and getattr(e, "title", None):
                all_text.append(e.title)
            if e and getattr(e, "description", None):
                all_text.append(e.description)
        except Exception:
            pass
    joined = "\n".join(all_text)
    for key, rx, thread in NEURO_KEYS:
        if rx.search(joined):
            return key, thread
    # if raw marker only, treat as phash_db title
    if isinstance(content, str) and re.fullmatch(r"\s*SATPAMBOT[_-]PHASH[_-]DB[_-]V1\s*", content or "", re.I):
        return "phash_db", "imagephising"
    return None, None

async def _ensure_thread(bot: discord.Client, log_ch: discord.TextChannel, name: str) -> discord.Thread|discord.TextChannel:
    """Find or create a public thread under log_ch with exact name."""
    try:
        # Active threads
        for th in log_ch.threads:
            if th.name == name:
                return th
        # Try archived (best effort)
        try:
            async for th in log_ch.archived_threads(limit=50, private=False, joined=False):
                if th.name == name:
                    await th.unarchive()
                    return th
        except Exception:
            pass
        # Create new
        return await log_ch.create_thread(name=name, auto_archive_duration=1440)
    except Exception:
        return log_ch

def _make_embed_from_json(title: str, body: str) -> discord.Embed:
    e = discord.Embed(title=title)
    # keep the json as code block for readability
    if body.strip().startswith("```"):
        desc = body.strip()
    else:
        desc = "```json\n" + body.strip()[:3950] + "\n```"
    e.description = desc
    return e

async def _send_singleton(key: str, args, kwargs) -> discord.Message:
    """Edit existing message instead of sending a new one."""
    msg = _singletons.get(key)
    if msg is None:
        # First time: send and remember
        out = await _ORIG_SEND(*args, **kwargs)
        if isinstance(out, discord.Message):
            _singletons[key] = out
        return out

    # Try edit existing
    try:
        # Build new params for edit()
        edit_kwargs = {}
        if "content" in kwargs:
            edit_kwargs["content"] = kwargs["content"]
        if "embed" in kwargs:
            edit_kwargs["embed"] = kwargs["embed"]
        if "embeds" in kwargs:
            edit_kwargs["embeds"] = kwargs["embeds"]
        await msg.edit(**edit_kwargs)
        return msg
    except Exception:
        # If edit fails (deleted or perms), re-send and replace handle
        out = await _ORIG_SEND(*args, **kwargs)
        if isinstance(out, discord.Message):
            _singletons[key] = out
        return out

async def _route_target(self: Messageable, args, kwargs):
    """Return a destination channel/thread (Messageable) according to policy."""
    cfg = get_conf()
    # hard gate: if public not allowed, we always route to log channel
    allow_public = str(cfg.get("NEURO_PUBLIC_OPEN", "0")).lower() in ("1", "true", "yes")
    log_id = int(str(cfg.get("LOG_CHANNEL_ID", "0")) or "0")
    log_ch = None
    bot = getattr(self, "bot", None) or getattr(self, "_state", None) and getattr(self._state, "client", None)

    if bot and log_id:
        log_ch = bot.get_channel(log_id)

    if not log_ch:
        return self  # fallback: no route available

    # Determine key & desired thread
    content = kwargs.get("content")
    embed = kwargs.get("embed")
    embeds = kwargs.get("embeds")
    key, thread_name = _extract_key_from_params(content, embed, embeds)

    # Always route to log main if public not allowed
    if not allow_public:
        if thread_name:
            return await _ensure_thread(bot, log_ch, thread_name)
        return log_ch

    # If public allowed, we still prefer log except for whitelisted
    return log_ch

async def _patched_send(self: Messageable, *args, **kwargs):
    # DM passthrough
    if isinstance(self, discord.DMChannel):
        return await _ORIG_SEND(self, *args, **kwargs)

    # Decide route
    dest = await _route_target(self, args, kwargs)

    # Singleton logic + auto-embed for JSON phash
    content = kwargs.get("content")
    embed = kwargs.get("embed")
    embeds = kwargs.get("embeds")

    key, thread_name = _extract_key_from_params(content, embed, embeds)

    # If we have a "title-only" phash line and the next message is JSON,
    # convert to a single embed (avoid double messages)
    if key == "phash_db":
        # if this call IS the pure title, just send singleton now
        if isinstance(content, str) and content.strip().upper().startswith("SATPAMBOT_PHASH_DB_V1") and not (embed or embeds):
            kwargs2 = dict(kwargs)
            # route to 'imagephising' thread
            kwargs2["content"] = "SATPAMBOT_PHASH_DB_V1"
            return await _send_singleton("phash_db", (dest,), kwargs2)

        # if this call looks like the JSON body with no embed, edit the previous singleton into an embed
        if isinstance(content, str) and _json_like(content) and not (embed or embeds):
            # Build embed
            e = _make_embed_from_json("SATPAMBOT_PHASH_DB_V1", content)
            kwargs2 = dict(kwargs)
            kwargs2["content"] = None
            kwargs2["embed"] = e
            return await _send_singleton("phash_db", (dest,), kwargs2)

    # Other singleton keys (status, neuro gate) — edit instead of re-send
    if key in ("neuro_gate", "status"):
        return await _send_singleton(key, (dest,), kwargs)

    # Default: just route and send normally
    return await _ORIG_SEND(dest, *args, **kwargs)

def setup(bot):
    # install once
    if getattr(Messageable, "_focus_log_router_installed", False):
        return
    Messageable.send = _patched_send
    Messageable._focus_log_router_installed = True
    try:
        bot.logger.info("[focus_log_router] active: forcing output to LOG channel & threads; singletons on")
    except Exception:
        print("[focus_log_router] active.", file=sys.stderr)
