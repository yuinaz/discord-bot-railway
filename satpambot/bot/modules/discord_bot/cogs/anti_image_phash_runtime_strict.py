from __future__ import annotations

# -*- coding: utf-8 -*-

import os
import time

"""
AntiImagePhashRuntime (STRICT)
--------------------------------
- Mengurangi false positive:
  * Hanya cek MIME/ekstensi: jpg/jpeg/webp
  * Ukuran minimum: ada edge >= MIN_EDGE
  * Threshold Hamming pHash kecil (DEFAULT 5)
- Preview mode bawaan: kirim kartu "Test Ban (Preview)" ke channel mod-command,
  tidak melakukan ban beneran. Ubah PREVIEW_MODE=False untuk autoban.
- Tidak menggunakan ENV; semua parameter di bawah.

Catatan:
- DB referensi diambil dari channel "log-botphising" (berdasar nama).
- Hanya memuat pHash sekali saat on_ready, tidak spam log.

File ini TIDAK menghapus file/konfigurasi lain; cukup tambahkan sebagai cog baru.
Kalau sudah puas, Anda bisa mengganti cog lama "anti_image_phash_runtime" dengan ini.
"""


import asyncio
import logging
from typing import Iterable, Optional, Set, Tuple

import discord
from discord.ext import commands, tasks
# DAILY LIMIT GLOBALS — auto-inserted
import time, os

# === pHash daily gate helper (auto-inserted) ===
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


# === KONFIGURASI ===
THRESHOLD = 5                 # Hamming distance maksimum agar dianggap match
MIN_EDGE = 256                # Abaikan gambar kecil (min sisi terpendek)
ALLOWED_EXTS = {".jpg", ".jpeg", ".webp"}
ALLOWED_MIME_PREFIX = ("image/jpeg", "image/webp")
PREVIEW_MODE = True           # True = hanya preview ke #mod-command
BAN_DELETE_MESSAGE_DAYS = 7   # Jika PREVIEW_MODE=False, hapus 7 hari chat
EXEMPT_ROLE_NAMES = {"Admin", "Moderator"}  # Tidak akan diban

# Channel nama yang dilindungi: tidak diban/auto-deleted dll.
SAFE_CHANNEL_NAMES = {"mod-command"}
REF_CHANNEL_NAME = "log-botphising"  # tempat referensi gambar/phash

LOG = logging.getLogger(__name__)


def _hex_to_bits(h: str) -> int:
    try:
        return int(h, 16)
    except Exception:
        return 0


def _hamming(a_hex: str, b_hex: str) -> int:
    return (_hex_to_bits(a_hex) ^ _hex_to_bits(b_hex)).bit_count()


def _best_size(width: int, height: int) -> int:
    return min(width or 0, height or 0)


async def _calc_phash_from_bytes(data: bytes) -> Optional[str]:
    """
    Coba hitung pHash. Prioritas pakai imagehash; fallback ke average hash buatan.
    Mengembalikan string hex 16 digit (64-bit) bila berhasil.
    """
    # try imagehash lib first
    try:
        from PIL import Image
        import imagehash  # type: ignore
        import io
        with Image.open(io.BytesIO(data)) as im:
            im = im.convert("RGB")
            # gunakan phash (bukan ahash/dhash) untuk kestabilan
            ph = imagehash.phash(im, hash_size=8)  # 8x8 => 64-bit
            return ph.hash.flatten().astype(int).tolist() and ph.__str__()
    except Exception:
        pass

    # fallback average hash manual (64-bit) — cukup untuk fallback kasar
    try:
        from PIL import Image
        import io
        with Image.open(io.BytesIO(data)) as im:
            im = im.convert("L").resize((8, 8))
            px = list(im.getdata())
            avg = sum(px) / len(px)
            bits = 0
            for i, val in enumerate(px):
                if val > avg:
                    bits |= (1 << i)
            return f"{bits:016x}"
    except Exception:
        return None


class AntiImagePhashRuntimeStrict(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._phash_db: Set[str] = set()
        self._loaded_once = False
        self._lock = asyncio.Lock()

    # ---------- util kecil ----------

    def _is_exempt_member(self, m: discord.Member) -> bool:
        rn = {r.name for r in getattr(m, "roles", [])}
        return bool(EXEMPT_ROLE_NAMES.intersection(rn))

    @staticmethod
    def _is_safe_channel(ch: discord.abc.GuildChannel) -> bool:
        name = getattr(ch, "name", "") or ""
        return name in SAFE_CHANNEL_NAMES

    @staticmethod
    def _is_allowed_attachment(att: discord.Attachment) -> bool:
        name = (att.filename or "").lower()
        # content_type bisa None; gunakan prefix check bila ada
        ctype = (att.content_type or "").lower()
        return (
            any(name.endswith(ext) for ext in ALLOWED_EXTS)
            or any(ctype.startswith(p) for p in ALLOWED_MIME_PREFIX)
        )

    # ---------- load DB dari thread/log ----------

    async def _load_reference_from_channel(self, guild: discord.Guild) -> int:
        count = 0
        try:
            ref_ch: Optional[discord.TextChannel] = discord.utils.get(
                guild.text_channels, name=REF_CHANNEL_NAME
            )
            if not ref_ch:
                LOG.warning("[phash-runtime.strict] ref channel '%s' tidak ditemukan", REF_CHANNEL_NAME)
                return 0

            async for msg in ref_ch.history(limit=500):
                for att in msg.attachments:
                    if not self._is_allowed_attachment(att):
                        continue
                    try:
                        data = await att.read()
                        ph = await _calc_phash_from_bytes(data)
                        if ph:
                            self._phash_db.add(ph)
                            count += 1
                    except Exception:
                        continue
        except Exception as e:
            LOG.exception("Gagal load referensi pHash: %r", e)
        return count

    # ---------- event hooks ----------

    @commands.Cog.listener()
    async def on_ready(self):
        # load sekali per proses
        if self._loaded_once:
            return
        self._loaded_once = True
        # muat DB untuk semua guild yang bot berada di dalamnya
        total = 0
        for g in self.bot.guilds:
            total += await self._load_reference_from_channel(g)
        LOG.info("[phash-runtime.strict] 🔐 Runtime pHash DB loaded: %d entries (thresh=%d, preview=%s)",
                 len(self._phash_db), THRESHOLD, PREVIEW_MODE)

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
        # abaikan bot & DM
        if not message.guild or message.author.bot:
            return

        # channel aman / mod-command: tidak ada aksi ban
        if self._is_safe_channel(message.channel):
            return

        member = message.author if isinstance(message.author, discord.Member) else None
        if member and self._is_exempt_member(member):
            return  # moderator/admin dikecualikan

        # proses attachments yang allowed
        to_check = [att for att in (message.attachments or []) if self._is_allowed_attachment(att)]
        if not to_check:
            return

        # iterasi lampiran
        for att in to_check:
            try:
                # cek dimensi dulu
                if att.width and att.height:
                    if _best_size(att.width, att.height) < MIN_EDGE:
                        continue

                data = await att.read(use_cached=True)
                ph = await _calc_phash_from_bytes(data)
                if not ph:
                    continue

                # bandingkan ke DB
                match = None
                for ref in self._phash_db:
                    if _hamming(ph, ref) <= THRESHOLD:
                        match = ref
                        break

                if not match:
                    continue

                # ——— MATCH: jalankan preview atau ban ———
                if PREVIEW_MODE:
                    # kirim embed simulasi ke #mod-command
                    ch = discord.utils.get(message.guild.text_channels, name="mod-command") or message.channel
                    e = discord.Embed(title="💀 Test Ban (Preview)",
                                      description="Ini **hanya simulasi**. Tidak ada aksi ban yang dilakukan.",
                                      color=0xED4245)
                    e.add_field(name="Target", value=f"{message.author.mention} (`{message.author.id}`)", inline=False)
                    e.add_field(name="Moderator", value=f"{self.bot.user.mention}", inline=True)
                    e.add_field(name="Reason", value="pHash match (strict) — preview", inline=False)
                    e.set_footer(text="SatpamBot • preview mode")
                    await ch.send(embed=e)
                else:
                    # ban langsung (one-shot) + delete history days
                    try:
                        await message.guild.ban(
                            message.author,
                            reason="pHash match (strict)",
                            delete_message_days=BAN_DELETE_MESSAGE_DAYS
                        )
                    except Exception as ex:
                        LOG.exception("Gagal ban: %r", ex)
                # hanya proses satu attachment pertama yang match
                break

            except Exception as e:
                LOG.exception("Gagal memproses attachment: %r", e)


async def setup(bot: commands.Bot):
    await bot.add_cog(AntiImagePhashRuntimeStrict(bot))
    LOG.info("[phash-runtime.strict] setup selesai")