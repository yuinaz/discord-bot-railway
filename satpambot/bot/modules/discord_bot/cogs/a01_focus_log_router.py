
import os
import logging
import discord

LOG = logging.getLogger(__name__)

# Keep reference to the framework's original .send()
_ORIG_SEND = discord.abc.Messageable.send

def _get_focus_id() -> int:
    raw = os.getenv("LOG_CHANNEL_ID") or ""
    try:
        return int(raw)
    except Exception:
        return 0

async def _patched_send(self, *args, **kwargs):
    """Redirect ANY Messageable.send to the focus log channel if it's not already that channel."""
    focus_id = _get_focus_id()
    try:
        current_id = getattr(self, "id", None)
    except Exception:
        current_id = None

    # If not configured or we're already in the focus channel, passthrough
    if not focus_id or (current_id == focus_id):
        return await _ORIG_SEND(self, *args, **kwargs)

    # Try to grab bot client from state
    bot = getattr(getattr(self, "_state", None), "client", None)
    channel = None
    if bot is not None:
        try:
            channel = bot.get_channel(focus_id)
        except Exception:
            channel = None

    # If we have a valid channel, post there instead
    if channel is not None:
        return await _ORIG_SEND(channel, *args, **kwargs)

    # Fallback: just send as-is
    return await _ORIG_SEND(self, *args, **kwargs)

def setup(bot):
    # Install patch once (idempotent)
    if getattr(discord.abc.Messageable.send, "__name__", "") != "_patched_send":
        discord.abc.Messageable.send = _patched_send
        LOG.info("[focus_log_router] active.")
