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

# ---- existing knobs from your env (no new keys, only fallbacks) ----
MARKER = os.getenv("PHASH_DB_MARKER", "SATPAMBOT_PHASH_DB_V1")
INBOX_THREAD_NAME = os.getenv("PHASH_INBOX_THREAD", "imagephising")
LOG_CHANNEL_ID = _getint("PHASH_LOG_CHANNEL_ID", 0)
AUTOBAN = (os.getenv("PHASH_AUTOBAN", "1") == "1")
BAN_REASON = os.getenv("PHASH_BAN_REASON", "Phishing image detected (hash match)")

# precedence: PHISH_HASH_THRESH_P > IMG_PHASH_MAX_DIST > default 8
HAMMING_THRESH = _getint("PHISH_HASH_THRESH_P", _getint("IMG_PHASH_MAX_DIST", 8))

# delete days precedence: PHISH_BAN_DELETE_DAYS > BAN_DELETE_DAYS > 0
BAN_DELETE_DAYS = _getint("PHISH_BAN_DELETE_DAYS", int(getattr(_cfg, "BAN_DELETE_DAYS", 0) or 0))

EXEMPT_CHANNELS = set([c.strip().lower() for c in (os.getenv("PHISH_EXEMPT_CHANNELS", "") or "").split(",") if c.strip()])
EXEMPT_ROLES = set([r.strip().lower() for r in (os.getenv("PHISH_EXEMPT_ROLES", "") or "").split(",") if r.strip()])
EXEMPT_FORUM = (os.getenv("PHISH_EXEMPT_FORUM", "0") == "1")

# Optional mirror for persistence
PHASH_STORE_FILE = os.getenv("PHISH_PHASH_STORE") or os.getenv("PHASH_STORE")

HEX16 = re.compile(r"^[0-9a-f]{16}$", re.I)
BLOCK_RE = re.compile(
    r"(?:^|\n)\s*%s\s*```(?:json)?\s*(\{.*?\})\s*```" % re.escape(MARKER),
    re.I | re.S,
)

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
    Pipeline yang kamu minta (tanpa ubah config):
    imagephising (thread) → user/siapa pun taruh gambar → bot hitung pHash → update pesan DB bertanda MARKER →
    seluruh guild ditegakkan: first-touchdown delete + autoban + EMBED pada channel kejadian.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db_hashes: List[str] = []
        self._ready_evt = asyncio.Event()
        self.watch_secs = _getint("PHASH_WATCH_SECS", 20)
        if self.watch_secs > 0:
            self._watcher.change_interval(seconds=self.watch_secs)
            self._watcher.start()

    # ------------ lifecycle ------------
    @commands.Cog.listener()
    async def on_ready(self):
        await self._reload_from_discord()
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
    async def _find_inbox_thread(self, guild: discord.Guild) -> Optional[discord.Thread]:
        name_l = INBOX_THREAD_NAME.strip().lower()
        try:
            for t in guild.threads:
                if isinstance(t, discord.Thread) and t.name.lower() == name_l:
                    return t
        except Exception:
            pass
        # search in text channels
        try:
            for ch in guild.text_channels:
                try:
                    async for th in ch.threads():
                        if th.name.lower() == name_l:
                            return th
                except Exception:
                    continue
        except Exception:
            pass
        return None

    async def _get_or_create_db_message(self, thread: discord.Thread) -> Optional[discord.Message]:
        # Cari pesan db (marker + fenced json) pada thread atau parentnya
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
        # Tidak ada → buat di parent agar mudah ditemukan
        parent = thread.parent if isinstance(thread.parent, discord.TextChannel) else thread
        try:
            payload = { "phash": [] }
            content = f"{MARKER}\n```json\n{json.dumps(payload, ensure_ascii=False)}\n```"
            return await parent.send(content)
        except Exception:
            return None

    async def _reload_from_discord(self):
        for guild in self.bot.guilds:
            try:
                thread = await self._find_inbox_thread(guild)
                if not isinstance(thread, discord.Thread):
                    continue
                msg = await self._get_or_create_db_message(thread)
                if not isinstance(msg, discord.Message) or not isinstance(msg.content, str):
                    continue
                m = BLOCK_RE.search(msg.content)
                if not m:
                    continue
                obj = json.loads(m.group(1))
                hashes = _norm_hashes(obj)
                if hashes:
                    self.db_hashes = hashes
                    await self._log(guild, f"♻️ pHash DB reloaded from Discord: {len(hashes)} entries (src: #{getattr(msg.channel, 'name','?')})")
                    # Optional mirror to file for persistence
                    if PHASH_STORE_FILE:
                        try:
                            Path(PHASH_STORE_FILE).parent.mkdir(parents=True, exist_ok=True)
                            Path(PHASH_STORE_FILE).write_text(json.dumps({"phash": hashes}, ensure_ascii=False, indent=2), encoding="utf-8")
                        except Exception:
                            pass
                    return
            except Exception:
                continue

    # watcher to refresh periodically
    @tasks.loop(seconds=20)
    async def _watcher(self):
        await self.bot.wait_until_ready()
        try:
            await self._reload_from_discord()
        except Exception:
            pass

    # ------------ indexer: image → pHash → append to DB message ------------
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
        # merge
        seen = set(current)
        merged = current + [h for h in new_hashes if h not in seen]
        obj = {"phash": merged}
        content = f"{MARKER}\n```json\n{json.dumps(obj, ensure_ascii=False)}\n```"
        try:
            await msg.edit(content=content)
            self.db_hashes = merged
            await self._log(getattr(thread, "guild", None), f"🧩 Added {len(new_hashes)} pHash → DB now {len(merged)} entries.")
            # mirror to file
            if PHASH_STORE_FILE:
                try:
                    Path(PHASH_STORE_FILE).parent.mkdir(parents=True, exist_ok=True)
                    Path(PHASH_STORE_FILE).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
                except Exception:
                    pass
        except Exception:
            return

    # ------------ moderation core ------------
    def _is_exempt(self, message: discord.Message) -> bool:
        # exempt channels by name
        try:
            if isinstance(message.channel, (discord.TextChannel, discord.Thread)):
                ch_name = message.channel.name.lower()
                # thread under forum?
                if EXEMPT_FORUM and isinstance(getattr(message.channel, "parent", None), discord.ForumChannel):
                    return True
                if ch_name in EXEMPT_CHANNELS:
                    return True
        except Exception:
            pass
        # exempt roles
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
            # Send to the SAME channel (first touchdown), as requested
            await message.channel.send(embed=embed)
        except Exception:
            pass

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        try:
            # 0) If message is the DB update block posted anywhere, reload DB
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

            # 1) Indexer: if new image(s) posted in the INBOX thread, compute pHash and append to DB
            if isinstance(message.channel, discord.Thread) and message.channel.name.lower() == INBOX_THREAD_NAME.lower():
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

            # 2) Enforcement: handle any other channels/threads
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

                # FIRST TOUCHDOWN: delete then autoban then announce embed in SAME channel
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
                return  # stop after first match

        except Exception:
            return

async def setup(bot: commands.Bot):
    await bot.add_cog(AntiImagePhashRuntime(bot))
