from __future__ import annotations
import os, re, json
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse

import discord
from discord.ext import commands, tasks

try:
    from ..helpers import guard_state
except Exception:
    guard_state = None

URL_POLICY_MARKER = "SATPAMBOT_URL_POLICY_V1"
WHITELIST_JSON = os.getenv("PHISH_URL_WHITELIST_JSON", "data/url_whitelist.json")
BLOCKLIST_JSON  = os.getenv("PHISH_URL_BLOCKLIST_JSON",  "data/url_blocklist.json")
BLOCKLIST_FILE = os.getenv("PHISH_URL_BLOCKLIST_FILE", "data/phish_url_blocklist.json")
WHITELIST_FILE = os.getenv("PHISH_URL_WHITELIST_FILE", "data/whitelist.txt")

def _boolenv(name: str, default: bool) -> bool:
    v = os.getenv(name)
    if v is None: return default
    return str(v).strip().lower() in ("1","true","yes","on")

AUTOBAN_DEFAULT         = _boolenv("PHISH_URL_AUTOBAN", True)
HEUR_AUTOBAN_DEFAULT    = _boolenv("PHISH_URL_HEUR_AUTOBAN", False)
NSFW_AUTOBAN_DEFAULT    = _boolenv("PHISH_URL_NSFW_AUTOBAN", True)

LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "0") or "0") or None

DOMAIN_URL_RE = re.compile(r"https?://[^\s/$.?#].[^\s]*", re.I)
BARE_DOMAIN_RE = re.compile(r"\b([a-z0-9\-]+\.)+[a-z]{2,}\b", re.I)

DEFAULT_ALLOWLIST = {
    "discord.com","discord.gg","discordapp.com",
    "github.com","gist.github.com","gitlab.com",
    "youtube.com","youtu.be",
    "google.com","play.google.com",
    "twitter.com","x.com",
    "facebook.com","m.facebook.com","fb.com",
    "instagram.com","tiktok.com","vm.tiktok.com",
    "twitch.tv","reddit.com",
    "microsoft.com","apple.com","cloudflare.com",
    "linkedin.com","paypal.com",
}

SUSPICIOUS_PATTERNS = [re.compile(r"xn--", re.I),
                       re.compile(r"discorcl|disc0rd|dlscord|dlsocrd", re.I),
                       re.compile(r"nitro[-]?(gift|promo|free)", re.I),
                       re.compile(r"airdrop", re.I)]
NSFW_PATTERNS = [re.compile(r"porn|sex|xxx|xnxx|xvideos|hentai|nsfw", re.I)]

def _norm_domain(d: str) -> str:
    d = d.strip().lower()
    if d.startswith("www."): d = d[4:]
    return d

def _extract_domains(text: str) -> List[str]:
    domains = set()
    for m in DOMAIN_URL_RE.finditer(text or ""):
        try:
            net = urlparse(m.group(0)).netloc
            if net: domains.add(_norm_domain(net))
        except Exception: pass
    for m in BARE_DOMAIN_RE.finditer(text or ""):
        domains.add(_norm_domain(m.group(0)))
    return list(domains)

def _load_allowlist() -> set[str]:
    allow = set()
    try:
        with open(WHITELIST_JSON, "r", encoding="utf-8") as f:
            obj = json.load(f) or {}
            if isinstance(obj, dict):
                arr = obj.get("allow", [])
                if isinstance(arr, list): allow |= { _norm_domain(x) for x in arr }
    except FileNotFoundError:
        try:
            raw = []
            with open(WHITELIST_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    s = line.strip()
                    if not s or s.startswith("#"): continue
                    raw.append(s)
            allow |= { _norm_domain(x) for x in raw }
            os.makedirs(os.path.dirname(WHITELIST_JSON), exist_ok=True)
            with open(WHITELIST_JSON, "w", encoding="utf-8") as wf:
                json.dump({"allow": sorted(allow)}, wf, indent=2, ensure_ascii=False)
        except Exception: pass
    except Exception: pass
    return allow

def _load_blocklist() -> set[str]:
    bl = set()
    try:
        with open(BLOCKLIST_JSON, "r", encoding="utf-8") as f:
            obj = json.load(f) or {}
            if isinstance(obj, dict):
                arr = obj.get("domains", [])
                if isinstance(arr, list):
                    bl |= { _norm_domain(x) for x in arr }
            elif isinstance(obj, list):
                bl |= { _norm_domain(x) for x in obj }
    except FileNotFoundError:
        try:
            with open(BLOCKLIST_FILE, "r", encoding="utf-8") as f:
                obj = json.load(f) or {}
                if isinstance(obj, dict) and "domains" in obj:
                    bl |= { _norm_domain(x) for x in obj["domains"] }
                elif isinstance(obj, list):
                    bl |= { _norm_domain(x) for x in obj }
            os.makedirs(os.path.dirname(BLOCKLIST_JSON), exist_ok=True)
            with open(BLOCKLIST_JSON, "w", encoding="utf-8") as wf:
                json.dump({"domains": sorted(bl)}, wf, indent=2, ensure_ascii=False)
        except Exception: pass
    except Exception: pass
    return bl

class UrlPolicy:
    def __init__(self):
        self.autoban = True
        self.heur_autoban = False
        self.nsfw_autoban = True
        self.allowlist = set(DEFAULT_ALLOWLIST) | _load_allowlist()
        self.blocklist = _load_blocklist()

    def merge_json(self, obj: Dict[str, Any]):
        if not isinstance(obj, dict): return
        if "autoban" in obj: self.autoban = bool(obj.get("autoban"))
        if "heur_autoban" in obj: self.heur_autoban = bool(obj.get("heur_autoban"))
        if "nsfw_autoban" in obj: self.nsfw_autoban = bool(obj.get("nsfw_autoban"))
        if "allow" in obj and isinstance(obj["allow"], list):
            self.allowlist |= { _norm_domain(x) for x in obj["allow"] }
        if "block" in obj and isinstance(obj["block"], list):
            self.blocklist |= { _norm_domain(x) for x in obj["block"] }

class AntiUrlPhishGuard(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.policy = UrlPolicy()
        self._ready = False
        self._refresh.start()

    def cog_unload(self):
        try: self._refresh.cancel()
        except Exception: pass

    @tasks.loop(minutes=2.0)
    async def _refresh(self):
        try:
            self.policy.allowlist = set(DEFAULT_ALLOWLIST) | _load_allowlist()
            self.policy.blocklist = _load_blocklist()
            if LOG_CHANNEL_ID:
                ch = self.bot.get_channel(LOG_CHANNEL_ID)
                if isinstance(ch, (discord.TextChannel, discord.Thread)):
                    try:
                        pins = await ch.pins()
                        for m in pins or []:
                            blob = None
                            if URL_POLICY_MARKER in (m.content or ""):
                                blob = self._extract_json_block(m.content)
                            for e in m.embeds or []:
                                if URL_POLICY_MARKER in (e.title or "") or URL_POLICY_MARKER in (e.description or ""):
                                    if e.description:
                                        blob = blob or self._extract_json_block(e.description)
                            if blob:
                                try:
                                    self.policy.merge_json(json.loads(blob))
                                except Exception: pass
                    except Exception: pass
            self._ready = True
        except Exception as e:
            print("[url-guard] refresh failed:", e)

    @_refresh.before_loop
    async def _before(self):
        await self.bot.wait_until_ready()

    def _extract_json_block(self, text: str) -> Optional[str]:
        m = re.search(r"```json\s+([\s\S]+?)```", text, re.I)
        if m: return m.group(1).strip()
        m = re.search(r"(\{[\s\S]+\})", text)
        return m.group(1).strip() if m else None

    def _looks_suspicious(self, domains: List[str], content: str) -> bool:
        return any(p.search(" ".join(domains)) for p in SUSPICIOUS_PATTERNS) or any(p.search(content or "") for p in SUSPICIOUS_PATTERNS)

    def _is_nsfw_domain(self, domains: List[str]) -> bool:
        for d in domains:
            for p in NSFW_PATTERNS:
                if p.search(d): return True
        return False

    def _can_punish(self, m: discord.Message) -> bool:
        if not m.guild or m.author.bot: return False
        perms = getattr(m.author, "guild_permissions", None)
        if perms and (perms.administrator or perms.manage_guild or perms.ban_members): return False
        return True

    async def _log(self, guild: discord.Guild, text: str):
        if not LOG_CHANNEL_ID: return
        ch = guild.get_channel(LOG_CHANNEL_ID) or self.bot.get_channel(LOG_CHANNEL_ID)
        try:
            if ch: await ch.send(text)
        except Exception: pass

    async def _delete_and_ban(self, message: discord.Message, reason: str):
        try: await message.delete()
        except Exception: pass
        try:
            member = message.guild.get_member(message.author.id) or await message.guild.fetch_member(message.author.id)
            await message.guild.ban(member, reason=reason, delete_message_days=1)
            await self._log(message.guild, f"⛔️ Auto-banned **{message.author}** karena {reason}")
        except Exception as e:
            await self._log(message.guild, f"⚠️ Gagal ban {message.author}: {e} (reason={reason})")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not self._ready or not message.guild: return
        if guard_state and not guard_state.should_process(getattr(message, "id", 0)): return
        if not self._can_punish(message): return

        content = message.content or ""
        domains = _extract_domains(content)
        if not domains: return

        domains = [d for d in domains if d not in self.policy.allowlist]
        if not domains: return

        bad = [d for d in domains if d in self.policy.blocklist]
        if bad and self.policy.autoban:
            await self._delete_and_ban(message, f"URL phishing (blocklist): {', '.join(bad)}")
            return

        if self.policy.nsfw_autoban and self._is_nsfw_domain(domains):
            await self._delete_and_ban(message, f"NSFW link (policy): {', '.join(domains[:3])}")
            return

        if self.policy.heur_autoban and self._looks_suspicious(domains, content):
            await self._delete_and_ban(message, f"URL phishing (heuristic): {', '.join(domains[:3])}")
            return

async def setup(bot: commands.Bot):
    await bot.add_cog(AntiUrlPhishGuard(bot))
