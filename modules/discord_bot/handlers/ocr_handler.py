# Enhanced OCR handler (auto 2025-08-09T12:25:01.102944Z)
import os, asyncio, logging, discord
from flask import current_app
from modules.discord_bot.helpers.ocr_check import extract_text_from_image, contains_prohibited_text
from modules.discord_bot.helpers.config_manager import get_flag

OCR_ENABLED = str(get_flag("OCR_ENABLED","true")).lower()=="true"
OCR_LANG = str(get_flag("OCR_LANG","eng+ind"))
OCR_MAX_SIZE_MB = float(get_flag("OCR_MAX_SIZE_MB","5"))
OCR_TIMEOUT_S = float(get_flag("OCR_TIMEOUT_S","12"))

def _too_big(att: discord.Attachment) -> bool:
    try:
        return (att.size or 0) > (OCR_MAX_SIZE_MB * 1024 * 1024)
    except Exception:
        return True

async def handle_ocr_check(message: discord.Message):
    if is_whitelisted_channel(getattr(message,'channel',None)) or is_exempt_user(getattr(message,'author',None)): return
    if not OCR_ENABLED or not message.attachments:
        return
    try:
        for att in message.attachments:
            if not (att.content_type or "").startswith("image"):
                continue
            if _too_big(att):
                logging.info(f"[OCR] skip large file name={att.filename} size={att.size}")
                continue
            img_bytes = await att.read()
            async def _run():
                return extract_text_from_image(img_bytes, lang=OCR_LANG)
            try:
                text = await asyncio.wait_for(_run(), timeout=OCR_TIMEOUT_S)
            except asyncio.TimeoutError:
                logging.warning("[OCR] Timeout")
                continue
            if not text:
                continue
            if contains_prohibited_text(text):
                try:
                    await message.delete()
                except Exception:
                    pass
                try:
                    await message.channel.send(f"⚠️ Pesan dari {message.author.mention} dihapus (teks terlarang terdeteksi).", delete_after=10)
                except Exception:
                    pass
                try:
                    if current_app:
                        current_app.logger.info(f"[OCR] removed user={message.author.id} text={text[:120]}")
                except Exception:
                    pass
    except Exception as e:
        logging.exception(f"[OCR] Error: {e}")
