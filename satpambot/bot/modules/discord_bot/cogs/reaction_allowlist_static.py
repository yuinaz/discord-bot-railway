# satpambot/bot/modules/discord_bot/cogs/reaction_allowlist_static.py
from __future__ import annotations
import os, re, logging
from typing import Set, List
import discord
from discord.ext import commands
log = logging.getLogger(__name__)
EMOJIS_TO_GUARD: Set[str] = {"✅"}
def _env_ids() -> Set[int]:
    out: Set[int] = set()
    for key in ("LOG_CHANNEL_ID","BAN_LOG_CHANNEL_ID","LOG_BAN_CHANNEL_ID","LOG_BOTPHISING_ID","LOG_BOTPHISHING_ID"):
        v = os.getenv(key); 
        if v:
            for tok in re.split(r"[\s,]+", v.strip()):
                if tok.isdigit(): out.add(int(tok))
    extra = os.getenv("REACTION_ALLOW_CH_IDS")
    if extra:
        for tok in re.split(r"[\s,]+", extra.strip()):
            if tok.isdigit(): out.add(int(tok))
    return out
def _env_name_patterns() -> List[str]:
    pats: List[str] = []
    v = os.getenv("LOG_CHANNEL_NAME"); 
    if v: pats.append(re.escape(v.strip()))
    extra = os.getenv("REACTION_ALLOW_NAMES")
    if extra: pats += [re.escape(x.strip()) for x in extra.split(",") if x.strip()]
    return pats
ALLOWED_NAME_PATTERNS: List[str] = [
    r"image.?phish(?:ing)?", r"image.?phis(?:ing|hing)?",
    r"log[-_ ]?bot?phish(?:ing)?", r"log[-_ ]?bot?phis(?:ing|hing)?",
    r"errorlog[-_ ]?bot",
] + _env_name_patterns()
ALLOWED_IDS: Set[int] = _env_ids()
def _is_name_allowed(name: str) -> bool:
    low = (name or "").lower(); 
    return any(re.search(p, low) for p in ALLOWED_NAME_PATTERNS)
class ReactionAllowlistStatic(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        log.info("[reaction-allowlist] patterns=%s ids=%s", ALLOWED_NAME_PATTERNS, sorted(ALLOWED_IDS))
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if str(payload.emoji) not in EMOJIS_TO_GUARD: return
        if not self.bot.user or payload.user_id != self.bot.user.id: return
        try:
            ch = self.bot.get_channel(payload.channel_id) or await self.bot.fetch_channel(payload.channel_id)
        except Exception: return
        ch_name = getattr(ch, "name", "") or getattr(getattr(ch, "parent", None), "name", "")
        allowed = (payload.channel_id in ALLOWED_IDS) or _is_name_allowed(ch_name)
        if allowed: return
        try:
            msg = await ch.fetch_message(payload.message_id)
            await msg.remove_reaction(payload.emoji, self.bot.user)
        except Exception as e:
            log.warning("[reaction-allowlist] remove failed: %r", e)
async def setup(bot: commands.Bot): await bot.add_cog(ReactionAllowlistStatic(bot))
