# modules/discord_bot/cogs/ocr_guard.py
from __future__ import annotations

import asyncio, io, logging, os
from typing import List, Optional

import discord
from discord.ext import commands
from PIL import Image

try:
    import numpy as np
except Exception:
    np = None

try:
    from rapidocr_onnxruntime import RapidOCR
except Exception:
    RapidOCR = None

try:
    import cv2
except Exception:
    cv2 = None

from modules.discord_bot.utils.mod_guard import claim
from modules.discord_bot.utils.threat_core import score_text

log = logging.getLogger("ocr_guard")

# Default OFF to keep Render Free light unless you enable it
OCR_ENABLED = os.getenv("OCR_ENABLED", "0") == "1"
OCR_TIMEOUT = int(os.getenv("OCR_TIMEOUT", "12"))
OCR_MAX_MB = float(os.getenv("OCR_MAX_MB", "3.5"))
OCR_MIN_W = int(os.getenv("OCR_MIN_W", "320"))
OCR_MIN_H = int(os.getenv("OCR_MIN_H", "320"))
OCR_RATE_PER_USER_SEC = int(os.getenv("OCR_RATE_PER_USER_SEC", "30"))
OCR_ACTION = os.getenv("OCR_ACTION", "log").lower()  # log | simulate | delete | kick
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "0"))
OCR_SCORE_THRESHOLD = int(os.getenv("OCR_SCORE_THRESHOLD", "4"))

def _preprocess_for_ocr(pil_img: Image.Image):
    img = pil_img.convert("RGB")
    if cv2 is None or np is None:
        w, h = img.size
        scale = 1.0
        if w < OCR_MIN_W or h < OCR_MIN_H:
            scale = max(OCR_MIN_W / w, OCR_MIN_H / h)
        if scale > 1.0:
            img = img.resize((int(w*scale), int(h*scale)))
        return (np.array(img) if np is not None else None)
    arr = np.array(img)
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    thr = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                cv2.THRESH_BINARY, 31, 11)
    proc = cv2.cvtColor(thr, cv2.COLOR_GRAY2RGB)
    h, w = proc.shape[:2]
    if w < OCR_MIN_W or h < OCR_MIN_H:
        scale = max(OCR_MIN_W / w, OCR_MIN_H / h)
        proc = cv2.resize(proc, (int(w*scale), int(h*scale)), interpolation=cv2.INTER_CUBIC)
    return proc

def _format_sim_embed(user: discord.abc.User, reasons: List[str]) -> discord.Embed:
    emb = discord.Embed(
        title="💀 Simulasi Ban oleh SatpamBot",
        description=f"{user.mention} terdeteksi mengirim pesan mencurigakan.\n(Pesan ini hanya simulasi untuk pengujian.)",
        color=discord.Color.dark_grey(),
    )
    emb.add_field(name="🧪 Simulasi testban", value="\u200b", inline=False)
    if reasons:
        emb.add_field(name="Detil Deteksi", value="• " + "\n• ".join(reasons), inline=False)
    return emb

class OCRGuard(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.ocr = RapidOCR() if (OCR_ENABLED and RapidOCR is not None and np is not None) else None
        self._user_last_ts: dict[int, float] = {}

    def _ratelimited(self, user_id: int) -> bool:
        now = asyncio.get_event_loop().time()
        last = self._user_last_ts.get(user_id, 0.0)
        if now - last < OCR_RATE_PER_USER_SEC:
            return True
        self._user_last_ts[user_id] = now
        return False

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not OCR_ENABLED or self.ocr is None:
            return
        if message.author.bot:
            return
        if not message.attachments:
            return
        if self._ratelimited(message.author.id):
            return

        targets = [a for a in message.attachments if (a.content_type or "").startswith("image/")]
        if not targets:
            return

        try:
            await asyncio.wait_for(self._inspect_attachments(message, targets), timeout=OCR_TIMEOUT)
        except asyncio.TimeoutError:
            log.warning("OCR timeout user=%s msg=%s", message.author.id, message.id)
        except Exception:
            log.exception("OCR error")

    async def _inspect_attachments(self, message: discord.Message, atts: List[discord.Attachment]):
        texts_total: List[str] = []

        for att in atts:
            size_mb = att.size / (1024 * 1024)
            if size_mb > OCR_MAX_MB:
                log.info("skip %s > %.2fMB", att.filename, size_mb); continue
            data = await att.read(use_cached=True)
            pil = Image.open(io.BytesIO(data)).convert("RGBA")
            proc = _preprocess_for_ocr(pil)
            if proc is None or self.ocr is None:
                continue
            result, _ = self.ocr(proc)  # [[box, text, conf], ...]
            lines = [r[1] for r in result or [] if len(r) >= 2]
            texts_total.extend(lines)

        if not texts_total:
            return
        final_score, reasons_final = score_text(texts_total)
        if final_score >= OCR_SCORE_THRESHOLD:
            await self._take_action(message, reasons_final)

    async def _take_action(self, message: discord.Message, reasons: List[str]):
        if not claim(message.id, "OCRGuard"):
            return

        ch_log: Optional[discord.TextChannel] = None
        if LOG_CHANNEL_ID and message.guild:
            ch = message.guild.get_channel(LOG_CHANNEL_ID)
            if isinstance(ch, discord.TextChannel):
                ch_log = ch

        action = OCR_ACTION
        if action == "simulate":
            emb = _format_sim_embed(message.author, reasons)
            if ch_log: await ch_log.send(embed=emb)
            else: await message.channel.send(embed=emb)
            return

        if action == "log":
            text = (
                f"⚠️ **Deteksi OCR**\n"
                f"Pengirim: {message.author.mention}\n"
                f"Channel: {message.channel.mention}\n"
                f"Alasan:\n• " + "\n• ".join(reasons)
            )
            if ch_log: await ch_log.send(text)
            else: await message.channel.send(text)
            return

        if action == "delete":
            try: await message.delete()
            except Exception: pass
            if ch_log:
                await ch_log.send(
                    f"🧹 Pesan {message.author.mention} dihapus (OCR). Alasan:\n• " + "\n• ".join(reasons)
                )
            return

        if action == "kick":
            try:
                if message.guild and isinstance(message.author, discord.Member):
                    await message.guild.kick(message.author, reason="OCR phishing/spam")
            except Exception:
                pass
            if ch_log:
                await ch_log.send(
                    f"👢 {message.author.mention} dikeluarkan (OCR). Alasan:\n• " + "\n• ".join(reasons)
                )
            return

async def setup(bot: commands.Bot):
    if OCR_ENABLED:
        if RapidOCR is None:
            log.error("RapidOCR not installed; OCRGuard disabled")
            return
        await bot.add_cog(OCRGuard(bot))
    else:
        log.info("OCRGuard disabled (OCR_ENABLED=0)")
