def _get_conf():
    try:
        from satpambot.config.compat_conf import get_conf
        return get_conf
    except Exception:
        try:
            from satpambot.config.runtime_memory import get_conf
            return get_conf
        except Exception:
            def _f(): return {}
            return _f

import json, contextlib
import discord
from satpambot.bot.utils import embed_scribe

def _to_text(body):
    if body is None:
        return ""
    if isinstance(body, str):
        return body
    try:
        return json.dumps(body, ensure_ascii=False, indent=2)
    except Exception:
        return str(body)

async def _ensure_target(bot):
    cfg = _get_conf()()
    log_id = int(str(cfg.get("LOG_CHANNEL_ID","0")) or 0)
    ch = bot.get_channel(log_id) if log_id else None
    if ch is None:
        for g in bot.guilds:
            with contextlib.suppress(Exception):
                return g.text_channels[0]
    return ch

async def _safe_edit_keeper(keeper: discord.Message | None, body):
    text = _to_text(body)
    e = discord.Embed(title="Neuro Lite Memory", description=text[:3900])
    bot = getattr(getattr(keeper, "guild", None), "_state", None)
    bot = getattr(bot, "client", None) if bot else None
    ch = getattr(keeper, "channel", None)
    if bot is None:
        with contextlib.suppress(Exception):
            bot = getattr(getattr(ch, "_state", None), "client", None)
    if bot is None:
        return False
    target = ch or await _ensure_target(bot)
    await embed_scribe.upsert(target, "SATPAMBOT_NEURO_LITE_MEMORY", e, pin=True, bot=bot, route=True)
    return True

async def upsert_pinned_memory(bot, payload):
    text = _to_text(payload)
    e = discord.Embed(title="Pinned Memory", description=text[:3900])
    ch = await _ensure_target(bot)
    if ch is None:
        return False
    await embed_scribe.upsert(ch, "SATPAMBOT_PINNED_MEMORY", e, pin=True, bot=bot, route=True)
    return True
