# a24_curriculum_auto_pin.py
# Auto-pin all curriculum reports sent to the configured report_channel_id (thread-safe).
import logging
from importlib import import_module
from discord.ext import commands

log = logging.getLogger(__name__)

class CurriculumAutoPin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._target_id = None

    def _load_target(self):
        try:
            a20 = import_module("satpambot.bot.modules.discord_bot.cogs.a20_curriculum_tk_sd")
            cfg = a20._load_cfg()
            cid = cfg.get("report_channel_id")
            if cid:
                self._target_id = int(cid)
                log.info("[curriculum_autopin] target set to id=%s", self._target_id)
        except Exception:
            log.warning("[curriculum_autopin] failed to load target id", exc_info=True)

    @commands.Cog.listener()
    async def on_ready(self):
        self._load_target()

    @commands.Cog.listener()
    async def on_message(self, message):
        if getattr(message, "author", None) is None:
            return
        if getattr(message.author, "bot", False) is False:
            return  # only consider bot's own messages
        if self._target_id is None:
            self._load_target()
        if self._target_id is None:
            return

        # Only messages in the configured channel/thread
        ch_id = int(getattr(message.channel, "id", 0) or 0)
        if ch_id != self._target_id:
            return

        # Heuristic: pin curriculum / progress messages
        text = (getattr(message, "content", "") or "")
        should_pin = ("Curriculum" in text) or ("TK→SD" in text) or ("progress" in text.lower())

        if not should_pin:
            return

        try:
            if not getattr(message, "pinned", False):
                await message.pin(reason="auto-pin curriculum report")
                log.info("[curriculum_autopin] pinned message id=%s in channel id=%s", message.id, ch_id)
        except Exception:
            log.warning("[curriculum_autopin] failed to pin message", exc_info=True)

async def setup(bot):
    await bot.add_cog(CurriculumAutoPin(bot))
