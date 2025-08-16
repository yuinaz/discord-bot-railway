from __future__ import annotations
import re, logging, asyncio
from datetime import datetime, timedelta, timezone
from typing import List, Optional
import discord
from discord.ext import commands
from satpambot.bot.modules.discord_bot.utils.actions import delete_message_safe
from ..helpers.log_utils import find_text_channel

log = logging.getLogger(__name__)

SUSPICIOUS_WORDS = {
    "verify","verifikasi","login","nitro","gift","hadiah","steam","wallet",
    "crypto","airdrop","bot token","2fa","sync","appeal","banned","suspend",
    "claim","redeem","unlock","kode","otp","payout",
}
PHISH_BRANDS = {"discord","steam","epic","roblox","valorant","garena","facebook","instagram","tiktok"}
SUSPICIOUS_TLDS = {".ru",".cn",".rest",".xyz",".click",".top",".gq",".tk",".ml",".cf",".icu",".zip",".mov",".mom"}
URL_RX = re.compile(r"https?://[^\s>]+", re.I)
INVITE_RX = re.compile(r"(?:https?://)?(?:discord(?:app)?\.com/invite/|discord\.gg/|dis\.gd/)([A-Za-z0-9-]+)", re.I)

TIMEOUT_MINUTES = int((__import__('os').getenv("FAST_GUARD_TIMEOUT_MINUTES") or "10"))
MENTION_THRESHOLD = int((__import__('os').getenv("FAST_GUARD_MENTION_THRESHOLD") or "6"))

def _extract_urls(text: str) -> List[str]:
    return URL_RX.findall(text or "")

def _looks_suspicious_text(text: str) -> bool:
    t = (text or "").lower()
    if sum(1 for w in SUSPICIOUS_WORDS if w in t) >= 2:
        return True
    if any(b in t for b in PHISH_BRANDS) and ("http://" in t or "https://" in t):
        return True
    return False

def _looks_suspicious_url(url: str) -> bool:
    u = url.lower()
    if any(u.endswith(tld) for tld in SUSPICIOUS_TLDS):
        return True
    if "xn--" in u:  # punycode
        return True
    # brand lookalike (very light)
    for brand in PHISH_BRANDS:
        if brand in u and "discord.com" not in u and "steamcommunity.com" not in u:
            return True
    return False

class FastGuard(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        try:
            if not message.guild or getattr(message.author, "bot", False):
                return
            content = getattr(message, "content", "") or ""
            urls = _extract_urls(content)
            mentions = getattr(message, "mentions", []) or []
            triggers = []

            if len(mentions) >= MENTION_THRESHOLD:
                triggers.append(f"mention>{MENTION_THRESHOLD}")

            if _looks_suspicious_text(content):
                triggers.append("text")

            if any(_looks_suspicious_url(u) for u in urls):
                triggers.append("url")

            # Discord invites outside current guild are suspicious here (FastGuard path)
            if INVITE_RX.search(content):
                triggers.append("invite")

            if not triggers:
                return

            # Action: timeout + delete
            timed_out = False
            try:
                until = datetime.now(timezone.utc) + timedelta(minutes=TIMEOUT_MINUTES)
                await message.author.edit(timeout=until, reason=f"FastGuard: {','.join(triggers)}")
                timed_out = True
            except Exception:
                pass
            try:
                await delete_message_safe(message, actor="FastGuard")
            except Exception:
                pass

            # Log
            try:
                ch = await find_text_channel(self.bot, name="log-botphising")
                if ch:
                    act = "timeout+delete" if timed_out else "delete"
                    await ch.send(f"🛡️ [FastGuard] {act} {message.author.mention} in {message.channel.mention} — reason: {', '.join(triggers)}")
            except Exception:
                pass
        except Exception:
            log.debug("FastGuard listener error", exc_info=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(FastGuard(bot))
