from __future__ import annotations

import os
import json
import time
from io import BytesIO
from pathlib import Path
from typing import List, Iterable, Optional, Tuple, Dict, Any

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

BAN_DELETE_DAYS = int(getattr(_cfg, "BAN_DELETE_DAYS", 0) or 0)

# ---------------- paths & loaders ----------------

def _data_dir() -> Path:
    return Path(os.getenv("DATA_DIR", "data")).resolve()

def _blocklist_path() -> Path:
    # dashboard dropzone path (new format)
    return (_data_dir() / "phish_lab" / "phash_blocklist.json").resolve()

def _legacy_path() -> Path:
    # legacy file used by older flows: {"phash": ["c1e08f...", ...]}
    return (_data_dir() / "phish_phash.json").resolve()

def _read_json(path: Path) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return None

_HEX16 = re = __import__("re").compile(r"^[0-9a-f]{16}$", __import__("re").I)

def _normalize_hashes_from_any(obj: Any) -> List[str]:
    """
    Accepts multiple shapes:
      - {"phash": ["<16-hex>", ...]}
      - [{"hash": "<16-hex>"}, ...]
      - ["<16-hex>", ...]
      - {"items": [{"hash": ...}, ...]}   (be permissive)
    Returns unique list of valid 16-hex pHash strings.
    """
    out: List[str] = []

    def _push(x: Any):
        if isinstance(x, str) and _HEX16.match(x.strip()):
            out.append(x.strip())

    if isinstance(obj, dict):
        # {"phash": [...]}
        if isinstance(obj.get("phash"), list):
            for h in obj["phash"]:
                _push(h)
        # {"items": [{"hash": ...}]}
        if isinstance(obj.get("items"), list):
            for it in obj["items"]:
                if isinstance(it, dict):
                    _push(it.get("hash"))
        # {"hashes": [...]} plain list
        if isinstance(obj.get("hashes"), list):
            for h in obj["hashes"]:
                _push(h)
    elif isinstance(obj, list):
        for it in obj:
            if isinstance(it, dict):
                _push(it.get("hash"))
            else:
                _push(it)

    # unique preserve order
    seen = set()
    uniq = []
    for h in out:
        if h not in seen:
            seen.add(h); uniq.append(h)
    return uniq

class _Store:
    def __init__(self, path_new: Path, path_legacy: Path):
        self.path_new = path_new
        self.path_legacy = path_legacy
        self.hashes: List[str] = []
        self.mt_new = 0.0
        self.mt_legacy = 0.0

# ---------------- hamming & compute ----------------

def _compute_phash(raw: bytes) -> Optional[str]:
    if _PIL_Image is None or _imagehash is None:
        return None
    try:
        im = _PIL_Image.open(BytesIO(raw)).convert("RGB")
        return str(_imagehash.phash(im))
    except Exception:
        return None

def _hamming_hex(a: str, b: str) -> Optional[int]:
    """Hamming distance between two 16-hex pHash strings."""
    if not a or not b or len(a) != len(b):
        return None
    try:
        ia = int(a, 16); ib = int(b, 16)
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

# ---------------- main cog ----------------

class AntiImagePhishBlocklist(commands.Cog):
    """
    Reads pHash blocklist from disk and takes action on matches.

    Sources supported:
      1) data/phish_lab/phash_blocklist.json (new)   -> list of {"hash": "<16-hex>"} or ["<16-hex>", ...]
      2) data/phish_phash.json (legacy)             -> {"phash": ["<16-hex>", ...]}

    Env overrides:
      DATA_DIR, PHASH_BLOCKLIST_PATH, PHASH_LEGACY_PATH,
      PHASH_WATCH_SECS (default: 10s),
      PHASH_HAMMING_THRESH (default: 8),
      PHASH_AUTOBAN ('1' to ban, '0' to only delete),
      PHASH_BAN_REASON, PHASH_LOG_CHANNEL_ID
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.store = _Store(
            Path(os.getenv("PHASH_BLOCKLIST_PATH") or _blocklist_path()),
            Path(os.getenv("PHASH_LEGACY_PATH") or _legacy_path()),
        )
        self.watch_secs = int(os.getenv("PHASH_WATCH_SECS", "10") or "10")
        self.threshold = int(os.getenv("PHASH_HAMMING_THRESH", "8") or "8")
        self.autoban = (os.getenv("PHASH_AUTOBAN", "1") == "1")
        self.ban_reason = os.getenv("PHASH_BAN_REASON", "Phishing image detected (hash match)")
        self.log_channel_id = int(os.getenv("PHASH_LOG_CHANNEL_ID", "0") or 0)

        self._reload_blocklist()
        if self.watch_secs > 0:
            self._watcher.change_interval(seconds=self.watch_secs)
            self._watcher.start()

    # ---- life ----
    @commands.Cog.listener()
    async def on_ready(self):
        # log on startup
        await self._log(None, f"🔐 pHash blocklist loaded: {len(self.store.hashes)} entries "
                              f"(thresh={self.threshold}, autoban={'ON' if self.autoban else 'OFF'})")

    # ---- internal ----
    def _reload_blocklist(self) -> None:
        nobj = _read_json(self.store.path_new)
        lobj = _read_json(self.store.path_legacy)
        arr = _normalize_hashes_from_any(nobj) + [h for h in _normalize_hashes_from_any(lobj) if h not in set(_normalize_hashes_from_any(nobj))]
        self.store.hashes = arr

        try: self.store.mt_new = self.store.path_new.stat().st_mtime
        except Exception: self.store.mt_new = 0.0
        try: self.store.mt_legacy = self.store.path_legacy.stat().st_mtime
        except Exception: self.store.mt_legacy = 0.0

    async def _log(self, guild: Optional[discord.Guild], text: str):
        ch = None
        if self.log_channel_id:
            ch = self.bot.get_channel(self.log_channel_id)
            if ch is None:
                try: ch = await self.bot.fetch_channel(self.log_channel_id)  # type: ignore
                except Exception: ch = None
        if isinstance(ch, (discord.TextChannel, discord.Thread)):
            try:
                await ch.send(text)
                return
            except Exception:
                pass
        print("[phish-blocklist]", text)

    # ---- watcher ----
    @tasks.loop(seconds=10)
    async def _watcher(self):
        await self.bot.wait_until_ready()
        try:
            mt_new = self.store.path_new.stat().st_mtime if self.store.path_new.exists() else 0.0
            mt_legacy = self.store.path_legacy.stat().st_mtime if self.store.path_legacy.exists() else 0.0
            if mt_new != self.store.mt_new or mt_legacy != self.store.mt_legacy:
                self._reload_blocklist()
                await self._log(None, f"♻️ pHash blocklist reloaded: {len(self.store.hashes)} entries")
        except Exception:
            pass

    # ---- core ----
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
            if not isinstance(message.channel, (discord.TextChannel, discord.Thread)):
                return
            if message.author.bot:
                return
            if not message.attachments:
                return

            # Only consider typical image extensions
            exts = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff", ".heic", ".heif")
            imgs = [a for a in message.attachments if isinstance(a.filename, str) and a.filename.lower().endswith(exts)]
            if not imgs:
                return

            # Pull bytes of first (or all) attachment(s)
            for att in imgs:
                try:
                    raw = await att.read()
                except Exception:
                    continue
                ph = _compute_phash(raw)
                if not ph:
                    continue
                d = _best_distance(ph, self.store.hashes)
                if d is None:
                    continue
                if d <= self.threshold:
                    # delete message
                    try:
                        await message.delete()
                    except Exception:
                        pass

                    # autoban
                    if self.autoban and isinstance(message.guild, discord.Guild):
                        try:
                            await message.guild.ban(
                                message.author,
                                reason=self.ban_reason,
                                delete_message_days=BAN_DELETE_DAYS,
                            )
                            await self._log(message.guild, f"🚫 Auto-banned {message.author} (Hamming={d} <= {self.threshold}) via pHash match.")
                        except Exception as e:
                            await self._log(message.guild, f"⚠️ Detected pHash match (Hamming={d}) but failed to ban {message.author}: {e}")
                    else:
                        await self._log(message.guild, f"🧹 Deleted phishing image from {message.author} (Hamming={d} <= {self.threshold})")
                    return  # stop after first match
        except Exception:
            # Be silent to avoid breaking other cogs
            return

async def setup(bot: commands.Bot):
    await bot.add_cog(AntiImagePhishBlocklist(bot))