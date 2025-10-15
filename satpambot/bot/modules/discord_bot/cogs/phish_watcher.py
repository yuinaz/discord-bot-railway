import hashlib, datetime as dt
import discord
from discord.ext import commands
from satpambot.bot.utils import embed_scribe, phash_db as PDB
def _load_conf_map() -> dict:
    # Legacy providers
    for mod in ("satpambot.config.compat_conf", "satpambot.config.runtime_memory"):
        try:
            m = __import__(mod, fromlist=["get_conf"])
            fn = getattr(m, "get_conf", None)
            if callable(fn):
                conf = fn()
                if isinstance(conf, dict):
                    return conf
        except Exception:
            pass
    # Fallback assemble
    conf = {}
    try:
        from satpambot.config.runtime import cfg as rcfg
        keys = [
            "PHASH_DB_PATH","PHISH_LOG_CHANNEL_ID","PHISH_WATCH_EXTS","PHISH_MIME_SNIFF_ENABLE",
            "PHISH_ENFORCE_MODE","PHISH_DELETE_MESSAGE_DAYS","PHISH_STRONG_DISTANCE","PHISH_MODERATE_DISTANCE",
            "PHISH_MIN_LABELED_DUPLICATES","PHISH_ACTION_STRONG","PHISH_ACTION_MODERATE",
            "PHISH_BAN_REASON_PRESET","PHISH_BAN_REASON_SUFFIX"
        ]
        for k in keys:
            v = rcfg(k)
            if v is not None:
                conf[k] = v
    except Exception:
        pass
    # Defaults
    conf.setdefault("PHASH_DB_PATH", "data/phash/SATPAMBOT_PHASH_DB_V1.json")
    conf.setdefault("PHISH_LOG_CHANNEL_ID", 0)
    conf.setdefault("PHISH_WATCH_EXTS", "png,jpg,jpeg,gif,webp")
    conf.setdefault("PHISH_MIME_SNIFF_ENABLE", True)
    conf.setdefault("PHISH_ENFORCE_MODE", "always")
    conf.setdefault("PHISH_DELETE_MESSAGE_DAYS", 7)
    conf.setdefault("PHISH_STRONG_DISTANCE", 4)
    conf.setdefault("PHISH_MODERATE_DISTANCE", 8)
    conf.setdefault("PHISH_MIN_LABELED_DUPLICATES", 2)
    conf.setdefault("PHISH_ACTION_STRONG", "ban")
    conf.setdefault("PHISH_ACTION_MODERATE", "delete")
    conf.setdefault("PHISH_BAN_REASON_PRESET", "compromised")
    conf.setdefault("PHISH_BAN_REASON_SUFFIX", "Anti-Image Guard (armed)")
    return conf

from typing import Any, Dict

class PhishWatcher(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.conf = _load_conf_map()
        self.db_path = self.conf.get("SATPAMBOT_PHASH_DB_V1_PATH", self.conf.get("PHASH_DB_PATH", "data/phash/SATPAMBOT_PHASH_DB_V1.json"))
        self.log_ch_id = int(self.conf.get("PHISH_LOG_CHANNEL_ID", 0))

        self.allow_exts = set(str(self.conf.get("PHISH_WATCH_EXTS","png,jpg,jpeg,gif,webp")).lower().split(","))
        self.sniff_on = bool(self.conf.get("PHISH_MIME_SNIFF_ENABLE", True))

        self.enforce_mode = str(self.conf.get("PHISH_ENFORCE_MODE","always")).lower()
        self.delete_days = int(self.conf.get("PHISH_DELETE_MESSAGE_DAYS", 7))

        self.d_strong = int(self.conf.get("PHISH_STRONG_DISTANCE", 4))
        self.d_mod = int(self.conf.get("PHISH_MODERATE_DISTANCE", 8))
        self.min_labeled = int(self.conf.get("PHISH_MIN_LABELED_DUPLICATES", 2))
        self.action_strong = str(self.conf.get("PHISH_ACTION_STRONG", "ban")).lower()
        self.action_mod = str(self.conf.get("PHISH_ACTION_MODERATE", "delete")).lower()
        self.timeout_secs = int(self.conf.get("PHISH_TIMEOUT_SECS", 0))

        self.require_label = (str(self.conf.get("PHISH_ENFORCE_REQUIRE_LABEL","")).lower().strip() or None)

        self.preset = str(self.conf.get("PHISH_BAN_REASON_PRESET","compromised")).lower()
        self.suffix = str(self.conf.get("PHISH_BAN_REASON_SUFFIX","Anti-Image Guard (armed)")).strip()

    def _target_log_channel(self, message: discord.Message):
        if self.log_ch_id:
            ch = self.bot.get_channel(self.log_ch_id)
            if ch: return ch
        return message.channel

    def _reason(self, why: str) -> str:
        head = {
            "spam": "Suspicious or spam account",
            "compromised": "Compromised or hacked account",
            "rules": "Breaking server rules",
            "other": "Other"
        }.get(self.preset, "Compromised or hacked account")
        if self.suffix and self.suffix not in head:
            return f"{head} — {why} — {self.suffix}"
        return f"{head} — {why}"

    def _sniff_kind(self, b: bytes, ext_guess: str) -> str:
        if not b or len(b) < 12:
            return ext_guess
        h = b[:12]
        try:
            if h[:3] == b"GIF" and h[3:6] in (b"87a", b"89a"): return "gif"
            if h[:8] == b"\x89PNG\r\n\x1a\n".encode('latin1'): return "png"
            if h[:3] == b"\xff\xd8\xff".encode('latin1'): return "jpg"
            if h[:4] == b"RIFF" and h[8:12] == b"WEBP": return "webp"
        except Exception:
            pass
        return ext_guess

    def _decide(self, db, ph, sh):
        dups = PDB.find_duplicates(db, phash=ph, max_distance=self.d_mod)
        if not dups:
            return ("none", None, 0, False)
        min_d = min(d for d,_ in dups)
        labeled = sum(1 for d,it in dups if (it.get("label","")== "phish"))
        exact_sha = any((it.get("sha256")==sh) for _,it in dups)
        if exact_sha or (min_d <= self.d_strong and labeled >= self.min_labeled):
            return ("strong", min_d, labeled, exact_sha)
        if min_d <= self.d_mod and labeled >= 1:
            return ("moderate", min_d, labeled, exact_sha)
        return ("none", min_d, labeled, exact_sha)

    async def _do_action(self, level, message, why):
        guild = message.guild
        member = message.author if isinstance(message.author, discord.Member) else None
        log_ch = self._target_log_channel(message)

        try: await message.delete()
        except Exception: pass

        act = self.action_strong if level=="strong" else self.action_mod
        if act == "none" or not guild or not member:
            return

        try:
            if act == "ban":
                await guild.ban(member, reason=self._reason(why), delete_message_days=self.delete_days)
            elif act == "kick":
                await guild.kick(member, reason=self._reason(why))
            elif act == "timeout" and self.timeout_secs>0:
                until = discord.utils.utcnow() + dt.timedelta(seconds=self.timeout_secs)
                await member.edit(timed_out_until=until, reason=self._reason(why))
            elif act == "delete":
                pass
        except Exception as e:
            try:
                await log_ch.send(embed=discord.Embed(title="Phish Action Error", description=str(e), color=0xe74c3c))
            except Exception:
                pass

    def _enforce_allowed(self) -> bool:
        return self.enforce_mode != "never"

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        try:
            if not message.guild or message.author.bot or not message.attachments:
                return
            if not self._enforce_allowed():
                return

            db = PDB.load_db(self.db_path)
            acted = False
            for att in message.attachments:
                name = (att.filename or "").lower()
                ext = name.rsplit(".",1)[-1] if "." in name else ""
                b = await att.read(use_cached=True)

                kind = self._sniff_kind(b, ext) if self.sniff_on else ext
                if kind not in self.allow_exts:
                    continue

                ph = PDB.compute_phash(b)
                sh = hashlib.sha256(b).hexdigest()

                level, min_d, labeled, exact = self._decide(db, ph, sh)

                if self.require_label:
                    dups = PDB.find_duplicates(db, phash=ph, max_distance=self.d_mod)
                    ok = any((it.get("label","")==self.require_label) for _,it in dups)
                    level = "strong" if ok else "none"

                if level != "none":
                    why = f"Match to known phish (min d={min_d}, labeled={labeled}{', exact' if exact else ''})"
                    await self._do_action(level, message, why)
                    acted = True
                    break

            log_ch = self._target_log_channel(message)
            try:
                desc = "enforced" if acted else "observed"
                e = discord.Embed(title="Phish Watch", description=desc, color=0xe67e22)
                e.add_field(name="Message", value=f"[jump]({message.jump_url})", inline=False)
                await log_ch.send(embed=e)
            except Exception:
                pass
        except Exception as e:
            try:
                log_ch = self._target_log_channel(message)
                await log_ch.send(embed=discord.Embed(title="Phish Watch Error", description=str(e), color=0xe74c3c))
            except Exception:
                pass

async def setup(bot: commands.Bot):
    await bot.add_cog(PhishWatcher(bot))