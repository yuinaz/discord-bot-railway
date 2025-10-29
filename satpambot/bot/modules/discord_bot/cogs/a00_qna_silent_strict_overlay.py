from __future__ import annotations
import os, logging, types, asyncio
import discord
from discord.ext import commands

log = logging.getLogger(__name__)

MARKER = "(auto-learn ping)"

def _env_true(k: str, default: bool=True) -> bool:
    v = os.getenv(k)
    if v is None:
        return default
    return str(v).strip().lower() in {"1","true","yes","on"}

def _qna_chan_id() -> int:
    for k in ("LEARNING_QNA_CHANNEL_ID","QNA_ISOLATION_CHANNEL_ID","QNA_CHANNEL_ID"):
        v = os.getenv(k)
        if v and v.isdigit():
            return int(v)
    return 0

class QnaSilentStrictOverlay(commands.Cog):
    """Absolutely suppress any '(auto-learn ping)'—delete instantly and prevent send."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.strict = _env_true("QNA_SUPPRESS_PING_STRICT", True)
        self.chan_id = _qna_chan_id()

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.strict:
            log.info("[qna-silent] strict OFF")
            return
        # Monkey-patch known source module if present
        try:
            from satpambot.bot.modules.discord_bot.cogs import neuro_autolearn_moderated_v2 as mod
            for name in ("_send_ping","send_ping","_post_ping","post_ping"):
                if hasattr(mod, name):
                    async def _noop(*a, **k): return None
                    setattr(mod, name, _noop)
            for name in ("PING_MARKER","PING_TEXT","MARKER"):
                if hasattr(mod, name):
                    setattr(mod, name, "")
            log.info("[qna-silent] patched neuro_autolearn_moderated_v2")
        except Exception:
            pass

        # Patch TextChannel.send to filter the marker (global safeguard)
        orig_send = discord.TextChannel.send
        async def send_filter(ch, *args, **kwargs):
            content = ""
            if args:
                content = args[0] if isinstance(args[0], str) else ""
            content = kwargs.get("content", content)
            if isinstance(content, str) and MARKER in content:
                log.info("[qna-silent] blocked ping at send()")
                class _Dummy:  # minimal message-like
                    id = 0; content = ""
                return _Dummy()
            return await orig_send(ch, *args, **kwargs)
        if getattr(discord.TextChannel.send, "_qna_silent_wrapped", False) is False:
            try:
                send_filter._qna_silent_wrapped = True  # type: ignore
                discord.TextChannel.send = send_filter  # type: ignore
                log.info("[qna-silent] send() wrapped (global)")
            except Exception as e:
                log.debug("[qna-silent] failed to wrap send(): %r", e)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not self.strict:
            return
        try:
            if message.author.id != self.bot.user.id:
                return
            if MARKER in (message.content or ""):
                await message.delete()
                log.info("[qna-silent] deleted stray ping msg id=%s", message.id)
        except Exception:
            pass

async def setup(bot: commands.Bot):
    await bot.add_cog(QnaSilentStrictOverlay(bot))
