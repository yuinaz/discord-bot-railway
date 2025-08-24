from __future__ import annotations

import asyncio
import json
import os
import time
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import discord
from discord.ext import commands, tasks

try:
    from PIL import Image as _PIL_Image
except Exception:  # pragma: no cover
    _PIL_Image = None

try:
    import imagehash as _imagehash
except Exception:  # pragma: no cover
    _imagehash = None


@dataclass
class _BlocklistStore:
    path_new: Path
    path_legacy: Path
    hashes: List[str]
    last_mtime_new: float
    last_mtime_legacy: float


def _data_dir() -> Path:
    return Path(os.getenv("DATA_DIR", "data")).resolve()


def _blocklist_path() -> Path:
    # dashboard dropzone path
    return (_data_dir() / "phish_lab" / "phash_blocklist.json").resolve()


def _legacy_path() -> Path:
    # legacy API path
    return (_data_dir() / "phish_phash.json").resolve()


def _load_list(p: Path) -> List[Dict]:
    try:
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8")) or []
    except Exception:
        pass
    return []


def _to_hashes(arr: List[Dict]) -> List[str]:
    out: List[str] = []
    for it in arr:
        if isinstance(it, dict):
            h = it.get("hash")
            if h:
                out.append(str(h))
        elif isinstance(it, str):
            out.append(it)
    # unique preserve order
    seen = set()
    uniq = []
    for h in out:
        if h not in seen:
            seen.add(h)
            uniq.append(h)
    return uniq


def _compute_phash(raw: bytes) -> Optional[str]:
    if _PIL_Image is None or _imagehash is None:
        return None
    try:
        im = _PIL_Image.open(BytesIO(raw)).convert("RGBA")
        return str(_imagehash.phash(im))
    except Exception:
        return None


def _hamming(a: str, b: str) -> Optional[int]:
    if _imagehash is None:
        return None
    try:
        return int(_imagehash.hex_to_hash(a) - _imagehash.hex_to_hash(b))  # type: ignore
    except Exception:
        return None


class AntiImagePhishBlocklist(commands.Cog):
    """
    COG: Membaca blocklist pHash dari disk dan auto-tindak saat match.
    - Baca dua sumber: data/phish_lab/phash_blocklist.json (baru) dan data/phish_phash.json (legacy).
    - Watcher reload saat file berubah.
    - on_message: cek attachment image, hitung pHash, bandingkan jarak Hamming <= threshold.
    - Aksi: delete pesan + (opsi) auto-ban.
    Konfigurasi (ENV):
      - DATA_DIR                : default 'data'
      - PHASH_BLOCKLIST_PATH    : override path blocklist baru
      - PHASH_LEGACY_PATH       : override path legacy
      - PHASH_WATCH_SECS        : interval reload file (default 10)
      - PHASH_HAMMING_THRESH    : default 8 (semakin kecil, semakin ketat)
      - PHASH_AUTOBAN           : '1' untuk ban, '0' hanya delete + log (default '1')
      - PHASH_BAN_REASON        : alasan ban
      - PHASH_LOG_CHANNEL_ID    : channel log (opsional)
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        base = _data_dir()
        p_new = Path(os.getenv("PHASH_BLOCKLIST_PATH") or _blocklist_path())
        p_legacy = Path(os.getenv("PHASH_LEGACY_PATH") or _legacy_path())
        self.store = _BlocklistStore(
            path_new=p_new,
            path_legacy=p_legacy,
            hashes=[],
            last_mtime_new=0.0,
            last_mtime_legacy=0.0,
        )
        self.watch_secs = int(os.getenv("PHASH_WATCH_SECS", "10") or "10")
        self.threshold = int(os.getenv("PHASH_HAMMING_THRESH", "8") or "8")
        self.autoban = (os.getenv("PHASH_AUTOBAN", "1") == "1")
        self.ban_reason = os.getenv("PHASH_BAN_REASON", "Phishing image detected (hash match)")
        self.log_channel_id = int(os.getenv("PHASH_LOG_CHANNEL_ID", "0") or 0)

        # initial load
        self._reload_blocklist()

        # start watcher
        if self.watch_secs > 0:
            self._watch_task.change_interval(seconds=self.watch_secs)
            self._watch_task.start()

    # ---- internal ----
    def _reload_blocklist(self) -> None:
        arr_new = _load_list(self.store.path_new)
        arr_legacy = _load_list(self.store.path_legacy)
        hashes = _to_hashes(arr_new) + [h for h in _to_hashes(arr_legacy) if h not in set(arr_new)]
        self.store.hashes = hashes
        # update mtime
        try:
            self.store.last_mtime_new = self.store.path_new.stat().st_mtime
        except Exception:
            self.store.last_mtime_new = 0.0
        try:
            self.store.last_mtime_legacy = self.store.path_legacy.stat().st_mtime
        except Exception:
            self.store.last_mtime_legacy = 0.0

    async def _log(self, guild: Optional[discord.Guild], text: str):
        ch = None
        if self.log_channel_id:
            ch = self.bot.get_channel(self.log_channel_id)
            if ch is None:
                try:
                    ch = await self.bot.fetch_channel(self.log_channel_id)  # type: ignore
                except Exception:
                    ch = None
        if isinstance(ch, (discord.TextChannel, discord.Thread)):
            try:
                await ch.send(text)
                return
            except Exception:
                pass
        # fallback: print
        print("[phish-blocklist]", text)

    # ---- watcher ----
    @tasks.loop(seconds=10)
    async def _watch_task(self):
        await self.bot.wait_until_ready()
        try:
            mt_new = self.store.path_new.stat().st_mtime if self.store.path_new.exists() else 0.0
            mt_legacy = self.store.path_legacy.stat().st_mtime if self.store.path_legacy.exists() else 0.0
            if mt_new != self.store.last_mtime_new or mt_legacy != self.store.last_mtime_legacy:
                self._reload_blocklist()
                await self._log(None, f"Reloaded pHash blocklist (count={len(self.store.hashes)})")
        except Exception:
            # ignore errors to keep loop alive
            pass

    @_watch_task.before_loop
    async def _before_watch(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(3)

    # ---- message hook ----
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if not isinstance(message.channel, (discord.TextChannel, discord.Thread)):
            return
        if not message.attachments:
            return
        if _imagehash is None or _PIL_Image is None:
            return

        # process each attachment image
        for att in message.attachments:
            if not (att.filename or "").lower().endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp")):
                continue
            try:
                raw = await att.read()
            except Exception:
                continue

            h = _compute_phash(raw)
            if not h:
                continue

            # compare against blocklist
            for bh in self.store.hashes:
                d = _hamming(h, bh)
                if d is None:
                    continue
                if d <= self.threshold:
                    # Match!
                    try:
                        await message.delete()
                    except Exception:
                        pass

                    # autoban if enabled
                    if self.autoban and isinstance(message.guild, discord.Guild):
                        try:
                            await message.guild.ban(message.author, reason=self.ban_reason, delete_message_days=0)
                            await self._log(message.guild, f"🚫 Auto-banned {message.author} (Hamming={d} <= {self.threshold}) using phash match.")
                        except Exception as e:
                            await self._log(message.guild, f"⚠️ Match pHash (Hamming={d}) but failed to ban {message.author}: {e}")
                    else:
                        await self._log(message.guild, f"⚠️ pHash match detected (Hamming={d}) from {message.author} — message deleted.")

                    # stop checking other hashes for this attachment
                    break


# loader compatible (discord.py 2.x uses async setup)
async def setup(bot: commands.Bot):
    await bot.add_cog(AntiImagePhishBlocklist(bot))
