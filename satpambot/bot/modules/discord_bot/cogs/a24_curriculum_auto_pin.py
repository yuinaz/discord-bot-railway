
# a24_curriculum_auto_pin.py
from discord.ext import commands
import logging
from importlib import import_module

log=logging.getLogger(__name__)
class CurriculumAutoPin(commands.Cog):
    def __init__(self, bot): self.bot=bot; self._target_id=None
    def _load_target(self):
        try:
            a20=import_module("satpambot.bot.modules.discord_bot.cogs.a20_curriculum_tk_sd")
            cfg=a20._load_cfg(); cid=cfg.get("report_channel_id")
            if cid: self._target_id=int(cid); log.info("[curriculum_autopin] target set to id=%s", self._target_id)
        except Exception: log.warning("[curriculum_autopin] failed to load target id", exc_info=True)
    @commands.Cog.listener()
    async def on_ready(self): self._load_target()
    @commands.Cog.listener()
    async def on_message(self, message):
        if getattr(message, "author", None) is None: return
        if getattr(message.author, "bot", False) is False: return
        if self._target_id is None: self._load_target()
        if self._target_id is None: return
        ch_id=int(getattr(message, "channel", None).id)
        if ch_id!=self._target_id: return
        text=(getattr(message, "content","") or "")
        if ("Daily Progress" in text) or ("Curriculum" in text) or ("XP:" in text) or ("NEURO-LITE" in text):
            try:
                if not getattr(message,"pinned",False):
                    await message.pin(reason="auto-pin curriculum report"); log.info("[curriculum_autopin] pinned message id=%s in channel id=%s", message.id, ch_id)
            except Exception: log.warning("[curriculum_autopin] failed to pin message", exc_info=True)
async def setup(bot): await bot.add_cog(CurriculumAutoPin(bot))