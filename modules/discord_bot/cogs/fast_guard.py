
from __future__ import annotations
import os, re, asyncio, time, collections
import discord
from discord.ext import commands

INVITE_RE = re.compile(r"(?:https?://)?(?:www\.)?(?:discord\.gg|discord\.com/invite)/([A-Za-z0-9-]+)", re.I)
URL_RE    = re.compile(r"https?://[^\s>)+\"']+", re.I)

def _split_set(value: str) -> set[str]:
    return {x.strip().lower() for x in value.split(",") if x.strip()}

class FastGuard(commands.Cog):
    """Fast ban untuk link phishing & undangan NSFW; sekarang dengan rate-limit & cache aman."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.enabled = os.getenv("FAST_GUARD_ENABLED", "1") != "0"
        self.bad_domains = _split_set(os.getenv("FAST_BAD_DOMAINS", ""))
        self.bad_keywords = _split_set(os.getenv("FAST_BAD_KEYWORDS", ""))
        self.strict_invite = os.getenv("FAST_INVITE_STRICT", "1") != "0"
        self.strict_on_error = os.getenv("FAST_INVITE_STRICT_ON_ERROR", "1") != "0"
        self.allow_guild_ids = {int(x) for x in _split_set(os.getenv("INVITE_ALLOW_GUILD_IDS", "")) if x.isdigit()}
        self.allow_codes = _split_set(os.getenv("INVITE_ALLOW_CODES", ""))
        self.del_secs = min(int(os.getenv("FAST_BAN_DELETE_SECONDS", str(7*24*3600))), 7*24*3600)

        # Rate-limit & cache for invite fetches
        self._fetch_limit = int(os.getenv("FAST_INVITE_FETCH_LIMIT", "8"))     # requests
        self._fetch_window = int(os.getenv("FAST_INVITE_FETCH_WINDOW", "60"))  # seconds
        self._fetch_times = collections.deque()  # timestamps
        self._invite_cache: dict[str, tuple[str, float]] = {}  # code -> (status, expire_at)
        self._invite_ttl = int(os.getenv("FAST_INVITE_CACHE_TTL", "900"))  # 15 min

    # --------------- helpers ---------------
    def _fetch_budget_ok(self) -> bool:
        now = time.time()
        while self._fetch_times and now - self._fetch_times[0] > self._fetch_window:
            self._fetch_times.popleft()
        return len(self._fetch_times) < self._fetch_limit

    def _mark_fetch(self):
        self._fetch_times.append(time.time())

    def _cache_get(self, code: str) -> str | None:
        ent = self._invite_cache.get(code.lower())
        if not ent:
            return None
        status, exp = ent
        if time.time() > exp:
            self._invite_cache.pop(code.lower(), None)
            return None
        return status

    def _cache_set(self, code: str, status: str, ttl: int | None = None):
        self._invite_cache[code.lower()] = (status, time.time() + (ttl or self._invite_ttl))

    async def _ban(self, message: discord.Message, reason: str) -> bool:
        try:
            await message.delete()
        except Exception:
            pass
        m = message.author
        if not isinstance(m, discord.Member):
            return False
        try:
            await message.guild.ban(m, reason=f"FastGuard: {reason}", delete_message_seconds=self.del_secs)
            return True
        except Exception:
            return False

    async def _check_invites(self, message: discord.Message) -> bool:
        content = message.content or ""
        codes = [m.group(1) for m in INVITE_RE.finditer(content)]
        if not codes:
            return False
        # Allowlist short-circuit
        if any(c.lower() in self.allow_codes for c in codes):
            return False

        code = codes[0].lower()
        cached = self._cache_get(code)
        if cached == "allow":
            return False
        if cached == "nsfw":
            return await self._ban(message, f"NSFW invite {code}")
        if cached == "unknown" and self.strict_invite:
            return await self._ban(message, f"Unknown/Untrusted invite {code} (cached)")

        # Budget check
        if not self._fetch_budget_ok():
            # Too many lookups; degrade based on policy
            if self.strict_invite:
                return await self._ban(message, f"Untrusted invite {code} (rate-limited)")
            return False

        # Try resolve via API
        self._mark_fetch()
        try:
            inv = await asyncio.wait_for(self.bot.fetch_invite(code, with_counts=False), timeout=2.0)
            # If invite guild is in allowlist -> allow
            if inv and getattr(inv, "guild", None) and getattr(inv.guild, "id", None) in self.allow_guild_ids:
                self._cache_set(code, "allow")
                return False
            # If channel nsfw -> ban
            if inv and getattr(inv, "channel", None) and getattr(inv.channel, "nsfw", False):
                self._cache_set(code, "nsfw")
                return await self._ban(message, f"NSFW invite {code}")
            # Unknown guild, handle by policy
            if self.strict_invite:
                self._cache_set(code, "unknown", ttl=120)  # short TTL to avoid hammering
                return await self._ban(message, f"Unknown/Untrusted invite {code}")
            self._cache_set(code, "unknown", ttl=120)
            return False
        except Exception as e:
            # Handle 429/Cloudflare
            msg = str(e)
            self._cache_set(code, "unknown", ttl=120)
            if "429" in msg or "rate limit" in msg.lower():
                if self.strict_on_error:
                    return await self._ban(message, f"Untrusted invite {code} (429)")
                return False
            # Other errors: best-effort policy
            if self.strict_on_error and self.strict_invite:
                return await self._ban(message, f"Untrusted invite {code} (error)")
            return False

    async def _check_urls(self, message: discord.Message) -> bool:
        content = (message.content or "").lower()
        hosts = [u.split('://',1)[-1].split('/',1)[0].split('@')[-1].lower() for u in URL_RE.findall(content)]
        hit = any(any(bd in h for bd in self.bad_domains) for h in hosts) or any(kw in content for kw in self.bad_keywords)
        if hit:
            return await self._ban(message, "phishing url/keywords")
        return False

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if (not self.enabled) or message.author.bot or (not message.guild):
            return
        # Skip command prefixes
        if message.content and message.content.lstrip().startswith(("!", "/")):
            return
        if await self._check_invites(message):
            return
        if await self._check_urls(message):
            return

async def setup(bot: commands.Bot):
    await bot.add_cog(FastGuard(bot))
