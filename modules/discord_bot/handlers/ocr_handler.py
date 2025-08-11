from ..helpers.ocr_check import extract_text, has_prohibited

async def handle_ocr_check(message, bot):
    # Only check attachments
    if not getattr(message, "attachments", None):
        return
    for att in message.attachments:
        try:
            b = await att.read()
        except Exception:
            continue
        txt = extract_text(b)
        if has_prohibited(txt):
            try:
                await message.delete()
            except Exception:
                pass
            break
