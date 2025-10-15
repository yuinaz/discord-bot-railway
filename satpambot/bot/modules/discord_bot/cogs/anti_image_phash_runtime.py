from __future__ import annotations

import asyncio
import json
import os
import re
from io import BytesIO
from pathlib import Path
from typing import Any, Iterable, List, Optional, Set

import discord
from discord.ext import commands, tasks
# DAILY LIMIT GLOBALS — auto-inserted
import time, os

# === pHash daily gate helper (auto-inserted) ===
import os
import time

try:
    _PHASH_REFRESH_SECONDS
except NameError:
    import os
_PHASH_REFRESH_SECONDS = int(os.getenv("PHASH_REFRESH_SECONDS", "86400"))  # default: 24 jam

try:
    _PHASH_LAST
except NameError:
    _PHASH_LAST = {}

def _phash_daily_gate(guild_id: int):
    try:
        import time
        now = time.time()
    except Exception:
        return True  # fallback: jangan blok
    last = _PHASH_LAST.get(guild_id, 0.0)
    if now - last < _PHASH_REFRESH_SECONDS:
        return False
    _PHASH_LAST[guild_id] = now
    return True
# === end helper ===

_PHASH_LAST_REFRESH: dict[int, float] = {}


# Optional deps
try:
    from PIL import Image as _PIL_Image
except Exception:
    _PIL_Image = None

try:
    import imagehash as _imagehash
except Exception:
    _imagehash = None

# Pull optional config from static_cfg when present
try:
    from satpambot.bot.modules.discord_bot.helpers import static_cfg as _cfg
except Exception:
    _cfg = None

def _getint(name: str, default: int) -> int:
    v = os.getenv(name)
    try:
        return int(v) if v is not None else default
    except Exception:
        return default

# ---- knobs (no rename; just read existing env; safe defaults) ----
MARKER = os.getenv("PHASH_DB_MARKER", "SATPAMBOT_PHASH_DB_V1")
# Accept multiple names separated by comma; default includes common variants used in your server
_DEFAULT_INBOX = "imagephising,imagelogphising,image-phising,image_phising,image-phishing,image_phishing"
INBOX_NAMES = [n.strip() for n in os.getenv("PHASH_INBOX_THREAD", _DEFAULT_INBOX).split(",") if n.strip()]
LOG_CHANNEL_ID = _getint("PHASH_LOG_CHANNEL_ID", 0)
AUTOBAN = (os.getenv("PHASH_AUTOBAN", "1") == "1")
BAN_REASON = os.getenv("PHASH_BAN_REASON", "Phishing image detected (hash match)")

HAMMING_THRESH = _getint("PHISH_HASH_THRESH_P", _getint("IMG_PHASH_MAX_DIST", 8))
BAN_DELETE_DAYS = _getint("PHISH_BAN_DELETE_DAYS", int(getattr(_cfg, "BAN_DELETE_DAYS", 0) or 0))

EXEMPT_CHANNELS = set([c.strip().lower() for c in (os.getenv("PHISH_EXEMPT_CHANNELS", "") or "").split(",") if c.strip()])
EXEMPT_ROLES = set([r.strip().lower() for r in (os.getenv("PHISH_EXEMPT_ROLES", "") or "").split(",") if r.strip()])
EXEMPT_FORUM = (os.getenv("PHISH_EXEMPT_FORUM", "0") == "1")

PHASH_STORE_FILE = os.getenv("PHISH_PHASH_STORE") or os.getenv("PHASH_STORE")

# Backfill controls
BACKFILL_ON_START = (os.getenv("PHASH_BACKFILL_ON_START", "1") == "1")
BACKFILL_MSG_LIMIT = _getint("PHASH_BACKFILL_MSG_LIMIT", 200)   # scan up to N recent messages
BACKFILL_IMG_LIMIT = _getint("PHASH_BACKFILL_IMG_LIMIT", 120)   # max images to hash per start
BACKFILL_SLEEP_MS = _getint("PHASH_BACKFILL_SLEEP_MS", 120)     # small delay to be gentle

HEX16 = re.compile(r"^[0-9a-f]{16}$", re.I)
BLOCK_RE = re.compile(
    r"(?:^|\n)\s*%s\s*```(?:json)?\s*(\{.*?\})\s*```" % re.escape(MARKER),
    re.I | re.S,
)
# fuzzy thread match if name not exactly provided
INBOX_FUZZY = re.compile(r"(image.*phis?h|phish.*image|image.*phish|imagelog.*phis?h)", re.I)

def _norm_hashes(obj: Any) -> List[str]:
    out: List[str] = []
    def push(x: Any):
        if isinstance(x, str) and HEX16.match(x.strip()):
            out.append(x.strip())
    if isinstance(obj, dict):
        if isinstance(obj.get("phash"), list):
            for h in obj["phash"]: push(h)
        if isinstance(obj.get("items"), list):
            for it in obj["items"]:
                if isinstance(it, dict): push(it.get("hash"))
        if isinstance(obj.get("hashes"), list):
            for h in obj["hashes"]: push(h)
    elif isinstance(obj, list):
        for it in obj:
            if isinstance(it, dict): push(it.get("hash"))
            else: push(it)
    # unique preserve order
    seen=set(); uniq=[]
    for h in out:
        if h not in seen:
            seen.add(h); uniq.append(h)
    return uniq

def _hamming_hex(a: str, b: str) -> Optional[int]:
    if not a or not b or len(a)!=len(b):
        return None
    try:
        ia=int(a,16); ib=int(b,16)
        return (ia ^ ib).bit_count()
    except Exception:
        return None

def _best_distance(ph: str, db: Iterable[str]) -> Optional[int]:
    best: Optional[int] = None
    for d in db:
        dist = _hamming_hex(ph, d)
        if dist is not None:
            best = dist if best is None else min(best, dist)
    return best

def _compute_phash(raw: bytes) -> Optional[str]:
    if _PIL_Image is None or _imagehash is None:
        return None
    try:
        im = _PIL_Image.open(BytesIO(raw)).convert("RGB")
        return str(_imagehash.phash(im))
    except Exception:
        return None

class AntiImagePhashRuntime(commands.Cog):
    """
    Auto-pipeline:
    - Cari thread inbox pHash (nama exact dari env atau fuzzy).
    - Startup: muat DB dari pesan marker; lalu BACKFILL: scan riwayat gambar di inbox → hitung pHash → append ke DB.
    - Jalan normal: siapa pun post gambar ke inbox → pHash otomatis ditambah ke DB.
    - Enforcement: channel mana pun → first-touchdown delete + autoban + embed.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db_hashes: List[str] = []
        self._ready_evt = asyncio.Event()
        self.watch_secs = _getint("PHASH_WATCH_SECS", 20)
        self._did_backfill = False
        if self.watch_secs > 0:
            self._watcher.change_interval(seconds=self.watch_secs)
            self._watcher.start()

    # ------------ lifecycle ------------
    @commands.Cog.listener()
    async def on_ready(self):
        await self._reload_from_discord()
        if BACKFILL_ON_START and not self._did_backfill:
            try:
                await self._backfill_from_inbox_images()
                self._did_backfill = True
            except Exception:
                pass
        self._ready_evt.set()
        await self._log(None, f"🔐 Runtime pHash DB loaded: {len(self.db_hashes)} entries (thresh={HAMMING_THRESH}, autoban={'ON' if AUTOBAN else 'OFF'})")

    # ------------ logging ------------
    async def _log(self, guild: Optional[discord.Guild], text: str):
        ch = None
        if LOG_CHANNEL_ID:
            ch = self.bot.get_channel(LOG_CHANNEL_ID)
            if ch is None:
                try:
                    ch = await self.bot.fetch_channel(LOG_CHANNEL_ID)  # type: ignore
                except Exception:
                    ch = None
        if isinstance(ch, (discord.TextChannel, discord.Thread)):
            try:
                await ch.send(text)
                return
            except Exception:
                pass
        print("[phash-runtime]", text)

    # ------------ helpers ------------
    async def _candidate_threads(self, guild: discord.Guild) -> List[discord.Thread]:
        names_l = {n.lower() for n in INBOX_NAMES}
        hits: List[discord.Thread] = []
        # active threads already cached
        for t in guild.threads:
            if not isinstance(t, discord.Thread):
                continue
            n = (t.name or "").lower()
            if n in names_l or INBOX_FUZZY.search(n or ""):
                hits.append(t)
        # sweep through text channels for active threads
        for ch in guild.text_channels:
            try:
                async for th in ch.threads():
                    n = (th.name or "").lower()
                    if n in names_l or INBOX_FUZZY.search(n or ""):
                        hits.append(th)
            except Exception:
                continue
        # dedup by id
        ded = []
        seen=set()
        for t in hits:
            if t.id not in seen:
                seen.add(t.id); ded.append(t)
        return ded

    async def _get_or_create_db_message(self, thread: discord.Thread) -> Optional[discord.Message]:
        # Search both thread and parent
        for src in [thread, thread.parent]:
            if not isinstance(src, (discord.TextChannel, discord.Thread)):
                continue
            try:
                async for msg in src.history(limit=100):
                    if isinstance(msg.content, str) and MARKER in msg.content:
                        m = BLOCK_RE.search(msg.content)
                        if m:
                            return msg
            except Exception:
                continue
        # Create under parent if missing
        parent = thread.parent if isinstance(thread.parent, discord.TextChannel) else thread
        try:
            payload = { "phash": [] }
            content = f"{MARKER}\n```json\n{json.dumps(payload, ensure_ascii=False)}\n```"
            return await parent.send(content)
        except Exception:
            return None

    async def _reload_from_discord(self):        # DAILY LIMIT — auto-inserted
        # Batasi reload pHash: maksimal sekali setiap _PHASH_REFRESH_SECONDS per guild
        gid = int(getattr(locals().get('guild', None), 'id', 0) or 0)
        if gid:
            last = _PHASH_LAST_REFRESH.get(gid, 0.0)
            now = time.time()
            if now - last < _PHASH_REFRESH_SECONDS:
                return  # sudah refresh baru-baru ini — skip untuk cegah spam/log
            _PHASH_LAST_REFRESH[gid] = now

        for guild in self.bot.guilds:
            try:
                threads = await self._candidate_threads(guild)
                if not threads:
                    continue
                # load DB from first found marker
                for t in threads:
                    msg = await self._get_or_create_db_message(t)
                    if not isinstance(msg, discord.Message) or not isinstance(msg.content, str):
                        continue
                    m = BLOCK_RE.search(msg.content)
                    if not m:
                        continue
                    obj = json.loads(m.group(1))
                    hashes = _norm_hashes(obj)
                    if hashes:
                        self.db_hashes = hashes
                        # pHash daily gate (auto-inserted)
                        try:
                            gid = int(getattr(guild, 'id', getattr(getattr(locals().get('msg', None), 'guild', None), 'id', 0)) or 0)
                        except Exception:
                            gid = 0
                        if not _phash_daily_gate(gid):
                            return
                        await self._log(guild, f"♻️ pHash DB loaded from Discord: {len(hashes)} entries (src: #{getattr(msg.channel,'name','?')})")
                        if PHASH_STORE_FILE:
                            try:
                                Path(PHASH_STORE_FILE).parent.mkdir(parents=True, exist_ok=True)
                                Path(PHASH_STORE_FILE).write_text(json.dumps({"phash": hashes}, ensure_ascii=False, indent=2), encoding="utf-8")
                            except Exception:
                                pass
                        break
                return
            except Exception:
                continue

    async def _append_hashes_to_db(self, thread: discord.Thread, new_hashes: List[str]):
        msg = await self._get_or_create_db_message(thread)
        if not isinstance(msg, discord.Message) or not isinstance(msg.content, str):
            return
        try:
            m = BLOCK_RE.search(msg.content)
            obj = json.loads(m.group(1)) if m else {"phash": []}
        except Exception:
            obj = {"phash": []}
        current = _norm_hashes(obj)
        seen = set(current)
        merged = current + [h for h in new_hashes if h not in seen]
        if merged == current:
            return
        obj = {"phash": merged}
        content = f"{MARKER}\n```json\n{json.dumps(obj, ensure_ascii=False)}\n```"
        try:
            await msg.edit(content=content)
            self.db_hashes = merged
            await self._log(getattr(thread, "guild", None), f"🧩 Added {len(merged)-len(current)} pHash → DB now {len(merged)} entries.")
            if PHASH_STORE_FILE:
                try:
                    Path(PHASH_STORE_FILE).parent.mkdir(parents=True, exist_ok=True)
                    Path(PHASH_STORE_FILE).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
                except Exception:
                    pass
        except Exception:
            return

    async def _backfill_from_inbox_images(self):
        """Scan recent images in candidate inbox threads and append missing pHashes to DB."""
        if _PIL_Image is None or _imagehash is None:
            return
        total_imgs = 0
        for guild in self.bot.guilds:
            try:
                threads = await self._candidate_threads(guild)
                for t in threads:
                    phs: List[str] = []
                    try:
                        async for msg in t.history(limit=BACKFILL_MSG_LIMIT):
                            if not msg.attachments:
                                continue
                            imgs = [a for a in msg.attachments if isinstance(a.filename, str) and a.filename.lower().endswith((".png",".jpg",".jpeg",".webp",".gif",".bmp",".tif",".tiff",".heic",".heif"))]
                            for att in imgs:
                                if total_imgs >= BACKFILL_IMG_LIMIT:
                                    break
                                try:
                                    raw = await att.read()
                                    ph = _compute_phash(raw)
                                    if ph and HEX16.match(ph):
                                        phs.append(ph); total_imgs += 1
                                except Exception:
                                    continue
                            if total_imgs >= BACKFILL_IMG_LIMIT:
                                break
                            # tiny sleep to be gentle
                            await asyncio.sleep(BACKFILL_SLEEP_MS / 1000.0)
                    except Exception:
                        continue
                    if phs:
                        await self._append_hashes_to_db(t, phs)
            except Exception:
                continue

    # watcher to refresh lightweight
    @tasks.loop(seconds=20)
    async def _watcher(self):
        await self.bot.wait_until_ready()
        try:
            await self._reload_from_discord()
        except Exception:
            pass

    # ------------ moderation & live index ------------
    def _is_exempt(self, message: discord.Message) -> bool:
        try:
            if isinstance(message.channel, (discord.TextChannel, discord.Thread)):
                ch_name = (message.channel.name or "").lower()
                if EXEMPT_FORUM and isinstance(getattr(message.channel, "parent", None), discord.ForumChannel):
                    return True
                if ch_name in EXEMPT_CHANNELS:
                    return True
        except Exception:
            pass
        try:
            if isinstance(message.author, discord.Member):
                role_names = {r.name.lower() for r in message.author.roles if isinstance(r, discord.Role)}
                if role_names & EXEMPT_ROLES:
                    return True
        except Exception:
            pass
        return False

    async def _send_ban_embed(self, message: discord.Message, ph: str, dist: int):
        try:
            embed = discord.Embed(
                title="🚫 Auto Ban: Phishing Image Detected",
                description=f"**User:** {message.author.mention}\n**Hamming:** `{dist}` (≤ `{HAMMING_THRESH}`)\n**pHash:** `{ph}`",
                color=discord.Color.red(),
            )
            embed.add_field(name="Channel", value=f"#{getattr(message.channel,'name','?')}", inline=True)
            embed.add_field(name="Reason", value=BAN_REASON, inline=True)
            await message.channel.send(embed=embed)
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
        try:
            # DB update block posted anywhere → reload
            if isinstance(message.content, str) and MARKER in message.content:
                m = BLOCK_RE.search(message.content)
                if m:
                    try:
                        obj = json.loads(m.group(1))
                        hashes = _norm_hashes(obj)
                        if hashes:
                            self.db_hashes = hashes
                            await self._log(message.guild if hasattr(message, "guild") else None,
                                            f"📥 pHash DB updated from message by {message.author} in #{getattr(message.channel, 'name', '?')} → {len(hashes)} entries")
                    except Exception:
                        pass

            # Live indexer: new images in inbox threads
            if isinstance(message.channel, discord.Thread):
                n = message.channel.name or ""
                if n and (n.lower() in {x.lower() for x in INBOX_NAMES} or INBOX_FUZZY.search(n)):
                    if message.attachments:
                        imgs = [a for a in message.attachments if isinstance(a.filename, str) and a.filename.lower().endswith((".png",".jpg",".jpeg",".webp",".gif",".bmp",".tif",".tiff",".heic",".heif"))]
                        phs: List[str] = []
                        for att in imgs:
                            try:
                                raw = await att.read()
                                ph = _compute_phash(raw)
                                if ph and HEX16.match(ph):
                                    phs.append(ph)
                            except Exception:
                                continue
                        if phs:
                            await self._append_hashes_to_db(message.channel, phs)

            # Enforcement
            if not isinstance(message.channel, (discord.TextChannel, discord.Thread)):
                return
            if message.author.bot:
                return
            if self._is_exempt(message):
                return
            if not message.attachments:
                return
            imgs = [a for a in message.attachments if isinstance(a.filename, str) and a.filename.lower().endswith((".png",".jpg",".jpeg",".webp",".gif",".bmp",".tif",".tiff",".heic",".heif"))]
            if not imgs or not self.db_hashes:
                return

            for att in imgs:
                try:
                    raw = await att.read()
                except Exception:
                    continue
                ph = _compute_phash(raw)
                if not ph:
                    continue
                d = _best_distance(ph, self.db_hashes)
                if d is None or d > HAMMING_THRESH:
                    continue

                try:
                    await message.delete()
                except Exception:
                    pass

                if AUTOBAN and isinstance(message.guild, discord.Guild):
                    try:
                        await message.guild.ban(
                            message.author,
                            reason=BAN_REASON,
                            delete_message_days=BAN_DELETE_DAYS,
                        )
                    except Exception as e:
                        await self._log(message.guild, f"⚠️ Match (Hamming={d}) but failed to ban {message.author}: {e}")
                await self._send_ban_embed(message, ph, d)
                await self._log(message.guild if hasattr(message, "guild") else None, f"✅ Enforced (Hamming={d} ≤ {HAMMING_THRESH}) on {message.author} in #{getattr(message.channel,'name','?')}")
                return

        except Exception:
            return

async def setup(bot: commands.Bot):
    await bot.add_cog(AntiImagePhashRuntime(bot))