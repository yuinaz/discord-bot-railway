from discord.ext import commands

# --- PATCH: robust fallback that does not import XPStore class ---
import logging as _logging
_log = _logging.getLogger(__name__)
async def _award_via_event(bot, author, amount: int, message=None, reason="qna/thread"):
    try:
        guild_id = getattr(getattr(message, "guild", None), "id", None) if message else None
        channel_id = getattr(getattr(message, "channel", None), "id", None) if message else None
        message_id = getattr(message, "id", None) if message else None
        bot.dispatch("xp_add",
            user_id=getattr(author, "id", None),
            amount=int(amount),
            guild_id=guild_id, channel_id=channel_id, message_id=message_id,
            reason=reason,
        )
        return True
    except Exception as e:
        _log.exception("[xp_force] event dispatch failed: %r", e)
        return False

import logging, asyncio, time

from typing import Optional

log = logging.getLogger(__name__)
try:
    from satpambot.bot.modules.discord_bot.services.xp_store import XPStore  # type: ignore
except Exception:
    XPStore = None  # type: ignore

FORCE_INCLUDE_QNA = True
COOLDOWN_SEC = 6

class XPForceIncludeOverlay(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._last = {}  # author_id -> ts

    def _allowed(self, message) -> bool:
        # Always include threads
        if getattr(message.channel, "type", None) and str(message.channel.type).endswith("thread"):
            return True
        # Include QNA if configured overlay is present
        if FORCE_INCLUDE_QNA:
            name = getattr(message.channel, "name", "") or ""
            if "qna" in name.lower():
                return True
        return False

    def _cool(self, author_id: int) -> bool:
        now = time.time()
        last = self._last.get(author_id, 0)
        if now - last >= COOLDOWN_SEC:
            self._last[author_id] = now
            return True
        return False

    @commands.Cog.listener("on_message")
    async def on_message(self, message):
        try:
            if message.author.bot:
                return
            if not self._allowed(message):
                return
            if not self._cool(message.author.id):
                return

            # Prefer direct award events; else fallback to XPStore file/upstash via compat overlay
            dispatched = 0
            for evt in ("xp_add", "xp.award", "satpam_xp"):
                try:
                    self.bot.dispatch(evt, message.author.id, +5, reason="force-include")
                    dispatched += 1
                except Exception:
                    pass

            if dispatched == 0 and XPStore and hasattr(XPStore, "load"):
                data = XPStore.load()
                users = data.setdefault("users", {})
                u = users.setdefault(str(message.author.id), {"xp": 0})
                u["xp"] = int(u.get("xp", 0)) + 5
                XPStore.save(data)
                log.info("[xp_force] fallback awarded +5 via XPStore compat (uid=%s)", message.author.id)
            else:
                log.debug("[xp_force] dispatched award events=%d (uid=%s)", dispatched, message.author.id)
        except Exception as e:
            log.warning("[xp_force] error: %s", e)

async def setup(bot):
    await bot.add_cog(XPForceIncludeOverlay(bot))