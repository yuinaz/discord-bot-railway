
import asyncio, re, hashlib, datetime as dt
from io import BytesIO
from typing import Optional

import discord
from discord.ext import commands

from satpambot.config.compat_conf import get_conf
from satpambot.bot.utils import embed_scribe
from satpambot.bot.utils import dupe_guard
from satpambot.bot.utils import phash_db as PDB

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
    # window like "00:00-04:00"
    try:
        a,b = window.split("-")
        h1,m1 = map(int, a.split(":"))
        h2,m2 = map(int, b.split(":"))
        s = now.replace(hour=h1, minute=m1, second=0, microsecond=0)
        e = now.replace(hour=h2, minute=m2, second=0, microsecond=0)
        if e <= s:
            # crosses midnight
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

    async def _log_embed(self, ch: discord.TextChannel, title: str, desc: str, color: int=0x2ecc71):
        e = discord.Embed(title=title, description=desc, color=color)
        await embed_scribe.upsert(ch, "PHISH_WATCH_LOG_V1", e, pin=False)

    def _should_watch_now(self) -> bool:
        if not self.quiet_on:
            return True
        now = _now_tz(self.quiet_tz)
        return _in_window(now, self.quiet_window)

    def _target_log_channel(self, message: discord.Message) -> discord.abc.Messageable:
        if self.log_ch_id:
            ch = self.bot.get_channel(self.log_ch_id)
            if ch: return ch
        return message.channel

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        try:
            if message.author.bot:
                return
            if not message.attachments:
                return
            if not self._should_watch_now():
                # still store hashes quietly (no GROQ)
                pass
            db = PDB.load_db(self.db_path)
            added_any = False
            summary_lines = []
            for att in message.attachments:
                name = (att.filename or "").lower()
                ext = name.rsplit(".",1)[-1] if "." in name else ""
                if ext not in self.allow_exts:
                    continue
                b = await att.read(use_cached=True)
                ph = PDB.compute_phash(b)
                sh = hashlib.sha256(b).hexdigest()
                item, is_new = PDB.upsert_item(db, phash=ph, sha256=sh, channel_id=message.channel.id, message_id=message.id, user_id=message.author.id, label="unknown", meta={"filename": name})
                added_any = added_any or is_new
                dups = PDB.find_duplicates(db, phash=ph, max_distance=8)
                if is_new:
                    summary_lines.append(f"🆕 {name} • phash={ph} • dups={len(dups)}")
                else:
                    summary_lines.append(f"↔️ {name} • DUP • phash={ph} • dups={len(dups)}")
            if added_any or summary_lines:
                PDB.save_db(db, self.db_path)
                # log once per message
                log_ch = self._target_log_channel(message)
                desc = "\n".join(summary_lines) or "no images"
                e = discord.Embed(title="Phish Watch", description=desc, color=0xe67e22)
                e.add_field(name="Message", value=f"[jump]({message.jump_url})", inline=False)
                await embed_scribe.upsert(log_ch, "SATPAMBOT_PHISH_WATCH_V1", e, pin=False)
        except Exception as e:
            # best-effort; don't crash the bot
            try:
                log_ch = self._target_log_channel(message)
                await self._log_embed(log_ch, "Phish Watch Error", str(e), color=0xe74c3c)
            except Exception:
                pass

async def setup(bot: commands.Bot):
    await bot.add_cog(PhishWatcher(bot))
