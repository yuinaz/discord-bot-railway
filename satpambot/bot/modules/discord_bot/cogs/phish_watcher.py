import hashlib, datetime as dt
import discord
from discord.ext import commands
try:
    from satpambot.config.compat_conf import get_conf  # prefer new compat layer
except Exception:  # pragma: no cover
    try:
        from satpambot.config.runtime_memory import get_conf  # fallback older projects
    except Exception:
        def get_conf():
            return {}
from satpambot.bot.utils import embed_scribe, phash_db as PDB
from satpambot.ml.neuro_lite_rewards import award_points_all

try:
    import pytz
except Exception:
    pytz = None

IMG_EXTS = {"png","jpg","jpeg","gif","webp"}

def _now_tz(tz_str: str | None) -> dt.datetime:
    now = dt.datetime.utcnow().replace(tzinfo=dt.timezone.utc)
    if not tz_str or pytz is None:
        return now
    try:
        tz = pytz.timezone(tz_str)
        return now.astimezone(tz)
    except Exception:
        return now

def _in_window(now: dt.datetime, window: str) -> bool:
    try:
        a,b = window.split("-")
        h1,m1 = map(int, a.split(":"))
        h2,m2 = map(int, b.split(":"))
        s = now.replace(hour=h1, minute=m1, second=0, microsecond=0)
        e = now.replace(hour=h2, minute=m2, second=0, microsecond=0)
        if e <= s:
            return not (s <= now < e)
        return s <= now < e
    except Exception:
        return False

class PhishWatcher(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.conf = get_conf()
        self.db_path = self.conf.get("SATPAMBOT_PHASH_DB_V1_PATH", "data/phash/SATPAMBOT_PHASH_DB_V1.json")
        self.log_ch_id = int(self.conf.get("PHISH_LOG_CHANNEL_ID", 0))
        self.quiet_on = bool(self.conf.get("QUIET_HOURS_ENABLED", True))
        self.quiet_window = self.conf.get("QUIET_HOURS_WINDOW","00:00-04:00")
        self.quiet_tz = self.conf.get("QUIET_HOURS_TZ","Asia/Jakarta")
        self.allow_exts = set(str(self.conf.get("PHISH_WATCH_EXTS","png,jpg,jpeg,gif,webp")).lower().split(","))

        self.enforce_mode = str(self.conf.get("PHISH_ENFORCE_MODE","always")).lower()
        self.action = str(self.conf.get("PHISH_ACTION","ban")).lower()
        self.hamming_threshold = int(self.conf.get("PHISH_HAMMING_THRESHOLD", 8))
        self.delete_days = int(self.conf.get("PHISH_DELETE_MESSAGE_DAYS", 1))
        src_ids = str(self.conf.get("PHISH_SOURCE_CHANNEL_IDS","")).strip()
        try:
            self.source_ids = {int(x) for x in src_ids.split(",") if x.strip()}
        except Exception:
            self.source_ids = set()
        self.require_label = (str(self.conf.get("PHISH_ENFORCE_REQUIRE_LABEL","phish")).lower().strip() or None)
        self.points_per_ban = int(self.conf.get("NEURO_POINTS_ON_PHISH", 1))
        self.neuro_dir = self.conf.get("NEURO_LITE_DIR", "data/neuro-lite")
        self.dry_run = bool(self.conf.get("PHISH_DRY_RUN", False))
        self.exempt_perms = bool(self.conf.get("PHISH_EXEMPT_STAFF", True))

    def _is_quiet_now(self) -> bool:
        if not self.quiet_on:
            return False
        now = _now_tz(self.quiet_tz)
        return _in_window(now, self.quiet_window)

    def _should_enforce_now(self) -> bool:
        if self.enforce_mode == "never":
            return False
        if self.enforce_mode == "always":
            return True
        if self.enforce_mode == "quiet-only":
            return self._is_quiet_now()
        return True

    def _target_log_channel(self, message: discord.Message):
        if self.log_ch_id:
            ch = self.bot.get_channel(self.log_ch_id)
            if ch:
                return ch
        return message.channel

    def _is_staff(self, m: discord.Member) -> bool:
        if not self.exempt_perms or not isinstance(m, discord.Member):
            return False
        perms = m.guild_permissions
        return perms.manage_messages or perms.kick_members or perms.ban_members or perms.administrator

    async def _enforce(self, message: discord.Message, why: str):
        guild = message.guild
        member = message.author if isinstance(message.author, discord.Member) else None
        log_ch = self._target_log_channel(message)
        if self._is_staff(member):
            await embed_scribe.upsert(log_ch, "SATPAMBOT_PHISH_WATCH_V1",
                discord.Embed(title="Phish Watch (SKIP - staff)", description=why, color=0xf1c40f), pin=False)
            return
        if self.action in ("ban","kick","delete-only"):
            try:
                await message.delete()
            except Exception:
                pass
        if self.action == "ban" and guild and member and not self.dry_run:
            try:
                await guild.ban(member, reason=why, delete_message_days=self.delete_days)
            except Exception:
                pass
        elif self.action == "kick" and guild and member and not self.dry_run:
            try:
                await guild.kick(member, reason=why)
            except Exception:
                pass
        try:
            award_points_all(self.neuro_dir, amount=self.points_per_ban, reason="phish_ban")
        except Exception:
            pass
        e = discord.Embed(title="Phish Enforcement", description=why, color=0xe74c3c)
        e.add_field(name="User", value=f"{message.author.mention}", inline=False)
        e.add_field(name="Message", value=f"[jump]({message.jump_url})", inline=False)
        await embed_scribe.upsert(log_ch, "SATPAMBOT_PHISH_ENFORCE_V1", e, pin=False)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        try:
            if not message.guild or message.author.bot:
                return
            if not message.attachments:
                return
            db = PDB.load_db(self.db_path)
            added_any = False
            any_enforced = False
            for att in message.attachments:
                name = (att.filename or "").lower()
                ext = name.rsplit(".",1)[-1] if "." in name else ""
                if ext not in self.allow_exts:
                    continue
                b = await att.read(use_cached=True)
                ph = PDB.compute_phash(b)
                sh = hashlib.sha256(b).hexdigest()
                label = "phish" if (self.source_ids and message.channel.id in self.source_ids) else "unknown"
                item, is_new = PDB.upsert_item(db, phash=ph, sha256=sh, channel_id=message.channel.id, message_id=message.id, user_id=message.author.id, label=label, meta={"filename": name})
                added_any = added_any or is_new
                dups = PDB.find_duplicates(db, phash=ph, max_distance=self.hamming_threshold)
                if dups:
                    enforce = True
                    if self.require_label:
                        enforce = any((it.get("label","") == self.require_label) for _, it in dups)
                    if enforce and self._should_enforce_now():
                        why = f"Match to known phish (<= {self.hamming_threshold} bits)"
                        await self._enforce(message, why=why)
                        any_enforced = True
                        break
            if added_any:
                PDB.save_db(db, self.db_path)
            log_ch = self._target_log_channel(message)
            desc = "enforced" if any_enforced else "observed"
            e = discord.Embed(title="Phish Watch", description=desc, color=0xe67e22)
            e.add_field(name="Message", value=f"[jump]({message.jump_url})", inline=False)
            await embed_scribe.upsert(log_ch, "SATPAMBOT_PHISH_WATCH_V1", e, pin=False)
        except Exception as e:
            try:
                log_ch = self._target_log_channel(message)
                await embed_scribe.upsert(log_ch, "SATPAMBOT_PHISH_WATCH_V1",
                    discord.Embed(title="Phish Watch Error", description=str(e), color=0xe74c3c), pin=False)
            except Exception:
                pass

async def setup(bot: commands.Bot):
    await bot.add_cog(PhishWatcher(bot))
