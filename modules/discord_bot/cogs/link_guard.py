# modules/discord_bot/cogs/link_guard.py
from __future__ import annotations

import asyncio, logging, os, re, unicodedata
from typing import List, Optional, Tuple, Set

import discord
from discord.ext import commands
from discord import ForumChannel

from modules.discord_bot.utils.mod_guard import claim
from modules.discord_bot.utils.threat_core import (
    extract_urls_from_message, score_urls, nfkc_lower
)

log = logging.getLogger("link_guard")

ENABLED = os.getenv("LINK_GUARD_ENABLED", "1") == "1"
ACTION = os.getenv("LINK_GUARD_ACTION", "delete").lower()  # log | delete | timeout | kick
WHITELIST_DOMAINS = {d.strip().lower() for d in os.getenv("LINK_WHITELIST", "").split(",") if d.strip()}
BLACKLIST_DOMAINS = {d.strip().lower() for d in os.getenv("LINK_BLACKLIST", "").split(",") if d.strip()}
SHORTENERS = {d.strip().lower() for d in os.getenv("LINK_SHORTENERS", "").split(",") if d.strip()} or None
RISKY_TLDS = {t.strip().lower() for t in os.getenv("RISKY_TLDS", "").split(",") if t.strip()} or None
PHISH_WORDS = {w.strip().lower() for w in os.getenv("PHISH_KEYWORDS", "").split(",") if w.strip()} or None
NSFW_WORDS = {w.strip().lower() for w in os.getenv("NSFW_KEYWORDS", "").split(",") if w.strip()} or None
FLAG_PUNYCODE = os.getenv("LINK_FLAG_PUNYCODE", "1") == "1"
RATE_PER_USER = int(os.getenv("LINK_RATE_PER_USER", "20"))
THRESHOLD = int(os.getenv("LINK_RISK_THRESHOLD", "4"))
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "0"))
IGNORE_THREADS = os.getenv("LINK_IGNORE_THREADS", "1") == "1"
IGNORE_FORUMS  = os.getenv("LINK_IGNORE_FORUMS",  "1") == "1"
NSFW_EXEMPT_WORDS = {w.strip().lower() for w in os.getenv("NSFW_EXEMPT_WORDS", "sexualized,seksualisasi").split(",") if w.strip()} or None
COMMAND_PREFIXES = tuple(p.strip() for p in os.getenv("COMMAND_PREFIXES", "!.,;:").split(",") if p.strip())

def _is_command_like(content: str) -> bool:
    text = (content or "").strip()
    if not text: return False
    return text.startswith("/") or text.startswith(COMMAND_PREFIXES)

class LinkGuard(commands.Cog):
    """Zero-network phishing/NSFW link detector. Render Free friendly."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._user_last: dict[int, float] = {}

    def _rate_limited(self, user_id: int) -> bool:
        now = asyncio.get_event_loop().time()
        last = self._user_last.get(user_id, 0.0)
        if now - last < RATE_PER_USER:
            return True
        self._user_last[user_id] = now
        return False

    def _should_ignore(self, msg: discord.Message) -> bool:
        if not ENABLED or msg.author.bot:
            return True
        # Ignore DMs/none
        if not hasattr(msg, "channel") or msg.channel is None:
            return True
        # Whitelist ForumChannel and Threads if toggled
        try:
            if IGNORE_FORUMS and isinstance(getattr(msg.channel, "parent", None), ForumChannel):
                return True
        except Exception:
            pass
        if IGNORE_THREADS and isinstance(msg.channel, discord.Thread):
            return True
        if not isinstance(msg.channel, (discord.TextChannel, discord.Thread)):
            return True
        try:
            m = msg.author
            if isinstance(m, discord.Member):
                if m.guild_permissions.manage_messages or m.guild_permissions.administrator:
                    return True
        except Exception:
            pass
        if _is_command_like(msg.content or \"\"):
            return True
        return False

    async def _take_action(self, msg: discord.Message, reasons: List[str]):
        if not claim(msg.id, "LinkGuard"):
            return

        action = ACTION
        log_ch: Optional[discord.TextChannel] = None
        if LOG_CHANNEL_ID and msg.guild:
            ch = msg.guild.get_channel(LOG_CHANNEL_ID)
            if isinstance(ch, discord.TextChannel):
                log_ch = ch

        who = f"{msg.author.mention} ({msg.author.id})"
        where = f"{msg.channel.mention}" if hasattr(msg.channel, "mention") else str(msg.channel)
        reason_text = "• " + "\n• ".join(reasons)

        if action == "delete":
            try: await msg.delete()
            except Exception: pass
            if log_ch: await log_ch.send(f"🧹 **Deleted suspicious message** dari {who} di {where}\n{reason_text}")
            return

        if action == "timeout":
            try:
                if msg.guild and isinstance(msg.author, discord.Member):
                    await msg.author.timeout(discord.utils.utcnow() + discord.timedelta(minutes=10),
                                             reason="Suspicious link (LinkGuard)")
            except Exception:
                pass
            try: await msg.delete()
            except Exception: pass
            if log_ch: await log_ch.send(f"⏳ **Timeout 10m + delete** {who} di {where}\n{reason_text}")
            return

        if action == "kick":
            try:
                if msg.guild and isinstance(msg.author, discord.Member):
                    await msg.guild.kick(msg.author, reason="Suspicious link (LinkGuard)")
            except Exception:
                pass
            if log_ch: await log_ch.send(f"👢 **Kick** {who} di {where}\n{reason_text}")
            return

        # default: log
        if log_ch:
            await log_ch.send(f"⚠️ **Suspicious link detected** dari {who} di {where}\n{reason_text}")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if self._should_ignore(message): return
        if self._rate_limited(message.author.id): return

        urls = extract_urls_from_message(message)
        if not urls:
            # handle pure NSFW spam without url
            text = nfkc_lower(message.content or "")
            custom_nsfw = NSFW_WORDS or set()
            if any(w in text for w in custom_nsfw):
                await self._take_action(message, ["nsfw keywords (no link)"])
            return

        score, reasons = score_urls(
            urls, message.content or "",
            whitelist=WHITELIST_DOMAINS,
            blacklist=BLACKLIST_DOMAINS,
            shorteners=SHORTENERS,
            risky_tlds=RISKY_TLDS,
            phish_words=PHISH_WORDS,
            nsfw_words=NSFW_WORDS,
            nsfw_exempt=NSFW_EXEMPT_WORDS,
            flag_punycode=FLAG_PUNYCODE,
        )
        if score >= THRESHOLD:
            await self._take_action(message, reasons)

async def setup(bot: commands.Bot):
    if ENABLED:
        await bot.add_cog(LinkGuard(bot))
    else:
        log.info("LinkGuard disabled (LINK_GUARD_ENABLED=0)")
