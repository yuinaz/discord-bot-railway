from modules.discord_bot.utils.actions import delete_message_safe
import asyncio
from ..helpers.ocr_check import extract_text, has_prohibited

async def handle_ocr_check(message, bot):
    # Hanya cek attachment
    if not getattr(message, "attachments", None):
        return
    for att in message.attachments:
        try:
            b = await att.read()
        except Exception:
            continue
        # Non-blocking: jalan di thread
        txt = await asyncio.to_thread(extract_text, b)
        if has_prohibited(txt):
            await delete_message_safe(message, actor='ocr_handler')
except Exception:
                pass
            break
