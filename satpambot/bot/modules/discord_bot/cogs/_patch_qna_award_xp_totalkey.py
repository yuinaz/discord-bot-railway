# PATCHED: prefer XP_TOTAL_KEY then XP_SENIOR_KEY for award target
try:
    from satpambot.bot.modules.discord_bot.cogs.qna_answer_award_xp_overlay import QnaAnswerAwardXP as _Orig
    from satpambot.bot.modules.discord_bot.cogs.qna_answer_award_xp_overlay import cfg_str as _cfg_str
except Exception:
    _Orig = None
    def _cfg_str(k,d): import os; return os.getenv(k,d)

if _Orig:
    # monkey patch __init__
    _orig_init = _Orig.__init__
    def _new_init(self, bot):
        _orig_init(self, bot)
        total_key = _cfg_str("XP_TOTAL_KEY", "") or ""
        if total_key:
            self.senior_key = total_key  # align with ladder key
    _Orig.__init__ = _new_init