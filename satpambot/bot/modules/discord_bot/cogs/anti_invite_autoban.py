from __future__ import annotations
import logging, os, re, time
from typing import Optional
import discord
from discord.ext import commands
from ..helpers.ban_utils import safe_ban_7d

log = logging.getLogger(__name__)
ENABLED = os.getenv("FAST_GUARD_ENABLED","1") not in {"0","false","no"}
NSFW_INVITE_AUTOBAN = os.getenv("NSFW_INVITE_AUTOBAN","true").lower() in {"1","true","yes"}
FETCH_LIMIT = int(os.getenv("FAST_INVITE_FETCH_LIMIT","3"))
FETCH_WINDOW = int(os.getenv("FAST_INVITE_FETCH_WINDOW","60"))
CACHE_TTL = int(os.getenv("FAST_INVITE_CACHE_TTL","3600"))
STRICT = os.getenv("FAST_INVITE_STRICT","1").lower() in {"1","true","yes"}
STRICT_ON_ERROR = os.getenv("FAST_INVITE_STRICT_ON_ERROR","1").lower() in {"1","true","yes"}

INVITE_RE = re.compile(r'(?:discord(?:\.gg|\.com/invite)/)([a-zA-Z0-9-]+)', re.I)

class AntiInviteAutoban(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._invite_cache: dict[str, tuple[float, Optional[discord.Invite]]] = {}
        self._ttl = CACHE_TTL
        self._fetch_count: dict[int, list[float]] = {}  # user.id -> timestamps

    def _rate(self, uid: int) -> bool:
        # allow only FETCH_LIMIT per FETCH_WINDOW seconds
        now = time.time()
        arr = [t for t in self._fetch_count.get(uid, []) if now - t < FETCH_WINDOW]
        ok = len(arr) < max(1, FETCH_LIMIT)
        if ok:
            arr.append(now)
            self._fetch_count[uid] = arr
        return ok

    async def _fetch_invite(self, code: str) -> Optional[discord.Invite]:
        now = time.time()
        c = self._invite_cache.get(code)
        if c and now - c[0] < self._ttl:
            return c[1]
        try:
            inv = await self.bot.fetch_invite(code, with_counts=False)
        except discord.NotFound:
            inv = None
        except discord.HTTPException:
            inv = None
        self._invite_cache[code] = (now, inv)
        return inv

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # THREAD/FORUM EXEMPTION — auto-inserted
        ch = getattr(message, "channel", None)
        if ch is not None:
            try:
                import discord
                # Exempt true Thread objects
                if isinstance(ch, getattr(discord, "Thread", tuple())):
                    return
                # Exempt thread-like channel types (public/private/news threads)
                ctype = getattr(ch, "type", None)
                if ctype in {
                    getattr(discord.ChannelType, "public_thread", None),
                    getattr(discord.ChannelType, "private_thread", None),
                    getattr(discord.ChannelType, "news_thread", None),
                }:
                    return
            except Exception:
                # If discord import/type checks fail, do not block normal flow
                pass
        if not ENABLED or message.author.bot or not message.guild:
            return
        m = INVITE_RE.search(message.content or "")
        if not m:
            return
        code = m.group(1)

        # default: allow self invites (no env toggle required)
        # fetch only if allowed by per-user rate
        if not self._rate(message.author.id):
            return

        inv = await self._fetch_invite(code)
        if not inv or not inv.guild:
            if STRICT or STRICT_ON_ERROR:
                try: await message.delete()
                except Exception: pass
            return

        target = inv.guild.id
        nsfw_level = getattr(inv.guild, "nsfw_level", -1) or -1

        if target == message.guild.id:
            return  # self invite
        # ban ONLY for NSFW guilds
        if nsfw_level >= 2 and NSFW_INVITE_AUTOBAN:
            try: await message.delete()
            except Exception: pass
            await safe_ban_7d(message.guild, message.author, reason=f"NSFW invite (nsfw_level={nsfw_level})")
            return
        # non‑NSFW: delete only if STRICT, otherwise allow
        if STRICT:
            try: await message.delete()
            except Exception: pass
