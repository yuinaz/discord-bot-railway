
import os
import logging
import discord

LOG = logging.getLogger(__name__)

# Keep a stable reference to what's installed *before* this final guard
_ORIG_SEND_FINAL = None

def _get_focus_id() -> int:
    raw = os.getenv("LOG_CHANNEL_ID") or ""
    try:
        return int(raw)
    except Exception:
        return 0

async def _final_wrapper(self, *args, **kwargs):
    """Final guard to prevent spammy Forbidden errors and ensure messages land in the log channel."""
    try:
        return await _ORIG_SEND_FINAL(self, *args, **kwargs)
    except discord.Forbidden as e:
        # On permission error, try force-route to focus channel
        focus_id = _get_focus_id()
        if focus_id and getattr(self, "id", None) != focus_id:
            bot = getattr(getattr(self, "_state", None), "client", None)
            chan = bot.get_channel(focus_id) if bot else None
            if chan:
                try:
                    return await _ORIG_SEND_FINAL(chan, *args, **kwargs)
                except Exception:
                    pass
        LOG.error("[focus_final] routed_send error; passthrough: %s", e)
        return None

def setup(bot):
    global _ORIG_SEND_FINAL
    if _ORIG_SEND_FINAL is None:
        _ORIG_SEND_FINAL = discord.abc.Messageable.send
        discord.abc.Messageable.send = _final_wrapper
        LOG.info("[focus_log_router_final] installed")
