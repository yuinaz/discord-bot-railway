
import logging, os, asyncio, inspect
import discord
from discord.ext import commands

log = logging.getLogger(__name__)

FOCUS_THREAD_NAME = os.getenv("FOCUS_THREAD_NAME", "").strip()
_ORIG_SEND = None

def _get_log_channel_id() -> int:
    raw = os.getenv("LOG_CHANNEL_ID", "0")
    try:
        return int(raw)
    except Exception:
        return 0

def _is_focus_dest(dest, focus_id: int) -> bool:
    try:
        if isinstance(dest, discord.TextChannel):
            return dest.id == focus_id
        if isinstance(dest, discord.Thread):
            # Only allow thread under the focus channel as well
            return dest.parent and dest.parent.id == focus_id
        return False
    except Exception:
        return False

def _bind_send(bot: commands.Bot):
    global _ORIG_SEND
    if _ORIG_SEND is not None:
        return

    _ORIG_SEND = discord.abc.Messageable.send

    async def _patched_send(self, *args, **kwargs):
        focus_id = _get_log_channel_id()
        # If destination already the focus channel or its thread: passthrough
        if focus_id and _is_focus_dest(self, focus_id):
            return await _ORIG_SEND(self, *args, **kwargs)

        # Replace destination with focus channel
        if focus_id:
            focus = bot.get_channel(focus_id)
            if focus is None:
                # Try via state cache as fallback
                try:
                    focus = self._state._get_guild_channel(focus_id)  # type: ignore
                except Exception:
                    focus = None
            if isinstance(focus, discord.TextChannel):
                # Optional: reuse a thread under focus channel by name
                if FOCUS_THREAD_NAME:
                    try:
                        thread = discord.utils.get(focus.threads, name=FOCUS_THREAD_NAME)
                        if thread is None:
                            # Try to find archived
                            archived = await focus.archived_threads().flatten()  # type: ignore
                            thread = discord.utils.get(archived, name=FOCUS_THREAD_NAME)
                        if isinstance(thread, discord.Thread):
                            return await thread.send(*args, **kwargs)
                    except Exception:
                        pass
                return await focus.send(*args, **kwargs)

        # If cannot resolve focus channel, last resort: do original
        return await _ORIG_SEND(self, *args, **kwargs)

    discord.abc.Messageable.send = _patched_send
    log.info("[focus_log_router] active.")

async def setup(bot: commands.Bot):
    # pure monkeypatch cogless helper
    _bind_send(bot)