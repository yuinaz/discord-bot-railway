from __future__ import annotations
import os, logging, types, inspect
from discord.ext import commands

log = logging.getLogger(__name__)

def _env_true(k: str, default: bool=True) -> bool:
    v = os.getenv(k)
    if v is None:
        return default
    return str(v).strip().lower() in {"1","true","yes","on"}

class QnaSilentModeOverlay(commands.Cog):
    """Disable noisy '(auto-learn ping)' at the source via monkey patching."""
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        if not _env_true("QNA_SUPPRESS_PING", True):
            log.info("[qna-silent] suppression disabled by ENV")
            return
        try:
            from satpambot.bot.modules.discord_bot.cogs import neuro_autolearn_moderated_v2 as mod
        except Exception as e:
            log.debug("[qna-silent] cannot import neuro_autolearn_moderated_v2: %r", e)
            return

        async def _noop(*args, **kwargs):
            return None

        patched = []
        for name in ("_send_ping","send_ping","_post_ping","post_ping"):
            if hasattr(mod, name):
                try:
                    setattr(mod, name, _noop)
                    patched.append(name)
                except Exception as e:
                    log.debug("[qna-silent] patch %s failed: %r", name, e)

        # Also neutralize marker if present (prevents other helpers using it)
        for name in ("PING_MARKER","PING_TEXT","MARKER"):
            if hasattr(mod, name):
                try:
                    setattr(mod, name, "")
                    patched.append(name)
                except Exception:
                    pass

        if patched:
            log.info("[qna-silent] suppressed ping functions/markers: %s", ", ".join(patched))
        else:
            log.info("[qna-silent] nothing to patch (module layout differs)")

async def setup(bot: commands.Bot):
    await bot.add_cog(QnaSilentModeOverlay(bot))
