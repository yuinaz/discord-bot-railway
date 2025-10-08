from __future__ import annotations
import os
from satpambot.bot.modules.discord_bot.helpers import threadlog
from satpambot.bot.modules.discord_bot.helpers import static_cfg
from satpambot.bot.modules.discord_bot.helpers import modlog, re, json
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

# --- NSFW soft exemptions (env-driven) ---
def _parse_csv_env(name: str, normalize_domain=False) -> set[str]:
    raw = os.getenv(name, "") or ""
    out = set()
    for part in re.split(r"[\s,;]+", raw):
        p = part.strip()
        if not p:
            continue
        if normalize_domain:
            p = _norm_domain(p)
        out.add(p.lower())
    return out

NSFW_SOFT_DOMAINS = _parse_csv_env("NSFW_SOFT_DOMAINS", normalize_domain=True)
NSFW_SOFT_KEYWORDS = _parse_csv_env("NSFW_SOFT_KEYWORDS", normalize_domain=False)
NSFW_SOFT_CHANNEL_NAMES = _parse_csv_env("NSFW_SOFT_CHANNEL_NAMES")
NSFW_SOFT_THREAD_NAMES = _parse_csv_env("NSFW_SOFT_THREAD_NAMES")
NSFW_SOFT_POLICY = (os.getenv("NSFW_SOFT_POLICY","ignore") or "ignore").strip().lower()
NSFW_SOFT_TIMEOUT_MIN = int((os.getenv("NSFW_SOFT_TIMEOUT_MIN","10") or "10").strip() or "10")


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


    def _apply_lists(self, lists_dict):
        try:
            self._wl_domains = set(lists_dict.get("wl_domains") or [])
            self._wl_patterns = lists_dict.get("wl_patterns") or []
            self._bl_domains = set(lists_dict.get("bl_domains") or [])
            self._bl_patterns = lists_dict.get("bl_patterns") or []
        except Exception:
            pass

    def _is_whitelisted_url(self, url: str) -> bool:
        if not url: 
            return False
        u = url.lower().strip()
        m = re.search(r"^(?:https?://)?([^/\s:]+)", u)
        domain = m.group(1) if m else ""
        if domain and (domain in self._wl_domains or any(domain.endswith("." + d) for d in self._wl_domains)):
            return True
        # NSFW soft exemptions
        if domain and domain in NSFW_SOFT_DOMAINS and NSFW_SOFT_POLICY == "ignore":
            return True
        # pattern allow
        for pat in self._wl_patterns:
            try:
                if re.search(pat, u, re.IGNORECASE):
                    return True
            except re.error:
                continue
        return False

    def _is_blocklisted_url(self, url: str) -> bool:
        if not url: 
            return False
        u = url.lower().strip()
        m = re.search(r"^(?:https?://)?([^/\s:]+)", u)
        domain = m.group(1) if m else ""
        if domain and (domain in self._bl_domains or any(domain.endswith("." + d) for d in self._bl_domains)):
            return True
        for pat in self._bl_patterns:
            try:
                if re.search(pat, u, re.IGNORECASE):
                    return True
            except re.error:
                continue
        return False

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


    def _is_soft_exempt(self, domains, content, channel):
        try:
            for d in domains or []:
                if _norm_domain(d) in NSFW_SOFT_DOMAINS:
                    return True
            lc = (content or "").lower()
            for kw in NSFW_SOFT_KEYWORDS:
                if kw and kw in lc:
                    return True
            try:
                cname = (getattr(channel, "name", "") or "").lower()
                if cname and (cname in NSFW_SOFT_CHANNEL_NAMES or cname in NSFW_SOFT_THREAD_NAMES):
                    return True
            except Exception:
                pass
        except Exception:
            pass
        return False

    def _can_punish(self, m: discord.Message) -> bool:
        if not m.guild or m.author.bot: return False
        perms = getattr(m.author, "guild_permissions", None)
        if perms and (perms.administrator or perms.manage_guild or perms.ban_members): return False
        return True

    async def _log(self, guild: discord.Guild, text: str):
        await threadlog.send_text(guild, text)

# === File-based policy (strict invite options) ============================
# Path: data/config/nsfw_invite_policy.json
# {
#   "autoban_enabled": true,
#   "ban_delete_days": 7,
#   "hint_emojis": ["💔","🥀"],
#   "new_account_days": 7,
#   "fallback_action": "ban",                 # ban|delete|timeout when unresolved & risk>=2
#   "fallback_timeout_minutes": 60,
#   "invite_unknown_action": "ban",           # ban|delete|timeout|ignore for non-whitelisted, non-NSFW-confirmed invites
#   "allowlist_guild_ids": [],                # e.g., [123456789012345678]
#   "allowlist_invite_codes": [],             # e.g., ["abcDEF"]
#   "nsfw_invite_keywords": ["nsfw","18+","xxx","hentai","porn"]
# }
import json
from pathlib import Path
_POLICY_DEFAULT = {
    "autoban_enabled": True,
    "ban_delete_days": 7,
    "hint_emojis": ["💔","🥀"],
    "new_account_days": 7,
    "fallback_action": "ban",
    "fallback_timeout_minutes": 60,
    "invite_unknown_action": "ban",
    "allowlist_guild_ids": [],
    "allowlist_invite_codes": [],
    "nsfw_invite_keywords": ["nsfw","18+","xxx","hentai","porn"]
}
def _policy_path() -> Path:
    candidates = []
    try:
        here = Path(__file__).resolve()
        for up in here.parents:
            candidates.append(up / "data" / "config" / "nsfw_invite_policy.json")
    except Exception:
        pass
    candidates.append(Path.cwd() / "data" / "config" / "nsfw_invite_policy.json")
    for p in candidates:
        if p.exists():
            return p
    return Path("data/config/nsfw_invite_policy.json")

def _load_policy_cached(self):
    try:
        cache = getattr(self, "_nsfw_invite_policy_cache", None)
        p = _policy_path()
        mtime = p.stat().st_mtime if p.exists() else -1
        if cache and cache.get("mtime") == mtime:
            return cache["data"]
        if p.exists():
            data = json.loads(p.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                data = dict(_POLICY_DEFAULT)
        else:
            data = dict(_POLICY_DEFAULT)
        merged = dict(_POLICY_DEFAULT)
        merged.update({k: v for k, v in data.items() if v is not None})
        self._nsfw_invite_policy_cache = {"mtime": mtime, "data": merged}
        return merged
    except Exception:
        return dict(_POLICY_DEFAULT)


async def _ban_author(self, message: discord.Message, reason: str):
    policy = self._load_policy_cached()
    delete_days = int(policy.get("ban_delete_days", 7))
    banned = False
    try:
        await message.guild.ban(
            message.author,
            reason=reason,
            delete_message_days=max(0, min(7, delete_days))
        )
        banned = True
    except Exception:
        try:
            await message.guild.kick(message.author, reason=reason)
            banned = True
        except Exception:
            pass
    if banned:
        try:
            await self._post_ban_embed(message, reason, tag="[auto-ban]")
        except Exception:
            pass
@commands.Cog.listener()
async def on_message(self, message: discord.Message):
    # --- PublicChatGate pre-send guard (auto-injected) ---
    gate = None
    try:
        gate = self.bot.get_cog("PublicChatGate")
    except Exception:
        pass
    try:
        if message.guild and gate and hasattr(gate, "should_allow_public_reply") and not gate.should_allow_public_reply(message):
            return
    except Exception:
        pass
    # --- end guard ---

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
    import re, datetime
    if not self._can_punish(message):
        return

    policy = self._load_policy_cached()
    content = message.content or ""

    # Collect URLs
    urls = set()
    try:
        urls.update(m.group(0) for m in DOMAIN_URL_RE.finditer(content))
    except Exception:
        pass
    try:
        urls.update(m.group(0) for m in BARE_DOMAIN_RE.finditer(content))
    except Exception:
        pass

    # NSFW porn-like domains → autoban
    if urls:
        for url in urls:
            if self._is_whitelisted_url(url) or self._is_soft_exempt(message, content, url):
                continue
            if bool(policy.get("autoban_enabled", True)) and self._is_nsfw_domain(url):
                try:
                    await message.delete()
                except Exception:
                    pass
                await self._ban_author(message, f"NSFW URL detected: {url}")
                await self._log(message.guild, f"[nsfw-url] BANNED {message.author} for {url}")
                return

    # Discord invites
    INVITE_URL_RE = re.compile(r'(?:https?://)?(?:discord(?:\\.gg|(?:app)?\\.com/invite))/([A-Za-z0-9-]+)', re.I)
    invite_codes = [m.group(1) for m in INVITE_URL_RE.finditer(content)]
    if not invite_codes:
        return

    cache = getattr(self, "_invite_nsfw_cache", None)
    if cache is None:
        self._invite_nsfw_cache = cache = {}
    if len(cache) > 1024:
        cache.clear()

    allow_guild_ids = set()
    try:
        allow_guild_ids = set(int(x) for x in policy.get("allowlist_guild_ids", []) if str(x).isdigit())
    except Exception:
        pass
    allow_codes = set(str(x).strip() for x in policy.get("allowlist_invite_codes", []) if str(x).strip())

    nsfw_keywords = [str(x).lower() for x in policy.get("nsfw_invite_keywords", []) if str(x).strip()]
    unknown_action = str(policy.get("invite_unknown_action", "ban")).lower().strip()

    resolved_any = False
    confirmed_nsfw = False
    confirmed_code = None

    # Try resolve each invite
    for code in invite_codes:
        full_url = f"https://discord.gg/{code}"
        if self._is_whitelisted_url(full_url) or self._is_soft_exempt(message, content, full_url) or (code in allow_codes):
            continue

        nsfw_target = cache.get(code)
        info = None
        if nsfw_target is None:
            try:
                try:
                    invite = await self.bot.fetch_invite(code, with_counts=False, with_expiration=False)
                except TypeError:
                    invite = await self.bot.fetch_invite(code)
            except Exception:
                invite = None

            nsfw_target = False
            if invite is not None:
                resolved_any = True
                g = getattr(invite, "guild", None)
                ch = getattr(invite, "channel", None)

                same_guild = False
                try:
                    same_guild = (getattr(g, "id", None) is not None and message.guild and g.id == message.guild.id)
                except Exception:
                    same_guild = False

                is_ch_nsfw = False
                try:
                    if ch is not None and hasattr(ch, "is_nsfw") and callable(ch.is_nsfw):
                        is_ch_nsfw = bool(ch.is_nsfw())
                except Exception:
                    pass

                is_guild_nsfw = False
                try:
                    lvl = getattr(g, "nsfw_level", None)
                    if lvl is not None:
                        s = str(lvl).lower()
                        if "explicit" in s or "age" in s or "nsfw" in s:
                            is_guild_nsfw = True
                    b = getattr(g, "nsfw", None)
                    if b is True:
                        is_guild_nsfw = True
                except Exception:
                    pass

                # Keyword inference on names (if flags missing)
                kw_hit = False
                try:
                    gname = (getattr(g, "name", "") or "").lower()
                    chname = (getattr(ch, "name", "") or "").lower()
                    for kw in nsfw_keywords:
                        if kw and (kw in gname or kw in chname):
                            kw_hit = True
                            break
                except Exception:
                    pass

                gid = getattr(g, "id", None)
                allowed = same_guild or (gid is not None and gid in allow_guild_ids)

                nsfw_target = (is_ch_nsfw or is_guild_nsfw or kw_hit) and not allowed
                info = {"gid": gid, "same": same_guild, "kw": kw_hit}

            cache[code] = nsfw_target

        if nsfw_target:
            confirmed_nsfw = True
            confirmed_code = code
            break

    if confirmed_nsfw and bool(policy.get("autoban_enabled", True)):
        try:
            await message.delete()
        except Exception:
            pass
        await self._ban_author(message, f"NSFW Discord invite detected: https://discord.gg/{confirmed_code}")
        await self._log(message.guild, f"[nsfw-invite] BANNED {message.author} for https://discord.gg/{confirmed_code}")
        return

    # Unknown/Unconfirmed invites handling (strict mode)
    if (not confirmed_nsfw):
        # If none resolved OR resolved but not allowed & not NSFW-confirmed:
        action = unknown_action  # ban|delete|timeout|ignore
        if action != "ignore":
            try:
                await message.delete()
            except Exception:
                pass
            if action == "ban":
                await self._ban_author(message, "Unconfirmed/unknown Discord invite (strict policy)")
            elif action == "timeout":
                try:
                    minutes = int(policy.get("fallback_timeout_minutes", 60))
                except Exception:
                    minutes = 60
                try:
                    until = datetime.datetime.utcnow() + datetime.timedelta(minutes=minutes)
                    await message.author.timeout(until=until, reason="Unknown Discord invite (strict policy)")
                except Exception:
                    pass
            await self._log(message.guild, f"[invite-unknown] action={action} user={message.author}")
            return


    async def _post_ban_embed(self, message: discord.Message, reason: str, tag: str = "[auto-ban]", url: str | None = None):


        """Kirim embed ban ke channel pelanggaran (WIB + alasan). Mirror Ban Log dimatikan — banlog_route menangani via on_member_ban."""


        from datetime import datetime, timezone, timedelta


        try:


            policy = self._load_policy_cached()


            purge_days = int(policy.get("ban_delete_days", 7))


        except Exception:


            purge_days = 7


    


        wib = timezone(timedelta(hours=7))


        ts = datetime.now(timezone.utc).astimezone(wib).strftime("%Y-%m-%d %H:%M WIB")


    


        mention = getattr(message.author, "mention", str(message.author))


        ch_name = getattr(message.channel, "name", "?")


    


        tag_l = (tag or "").lower()


        rsn_l = (reason or "").lower()


        category = "NSFW" if "nsfw" in tag_l or "nsfw" in rsn_l else ("Phishing/Unknown" if "invite" in tag_l or "unknown" in tag_l or (url and "discord.gg" in str(url).lower()) else "Mencurigakan")


        default_reason = "kirim link NSFW" if category == "NSFW" else "kirim link phishing/undangan mencurigakan"


        alasan = reason or default_reason


    


        lines = [f"{mention} terdeteksi mengirim pesan mencurigakan."]


        if url: lines.append(f"URL: {url}")


        lines.append(f"Alasan mencurigakan: {alasan} ({category})")


        lines.append(f"Pesan telah dihapus. Pengguna telah di-ban. (Riwayat {purge_days} hari dihapus)")


        description = "\n".join(lines)


    


        emb = discord.Embed(


            title="💀 Ban Otomatis oleh SatpamBot",


            description=description,


            colour=discord.Colour.red(),


        )


        emb.set_footer(text=f"{tag} • #{ch_name} • {ts}")


    


        try:


            await message.channel.send(embed=emb)


        except Exception:


            pass


    


        # Mirror Ban Log dimatikan (hindari duplikat); banlog_route on_member_ban akan menulis log.
