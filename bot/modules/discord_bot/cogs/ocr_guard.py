from __future__ import annotations
import logging, io
import discord
from discord.ext import commands
from modules.discord_bot.utils.actions import delete_message_safe
from modules.discord_bot.helpers.log_utils import find_text_channel

log = logging.getLogger(__name__)

KEYWORDS = {"verify","login","nitro","gift","claim","appeal","kode","otp","wallet","2fa"}

def _ocr_text(data: bytes) -> str | None:
    try:
        from PIL import Image
        import pytesseract
        with Image.open(io.BytesIO(data)) as im:
            im = im.convert("RGB")
            return pytesseract.image_to_string(im)
    except Exception:
        return None

class OCRGuard(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        try:
            if not message.guild or getattr(message.author, "bot", False):
                return
            atts = getattr(message, "attachments", []) or []
            for att in atts:
                if not (att.content_type or "").startswith("image"):
                    continue
                if att.size and att.size > 4 * 1024 * 1024:
                    continue
                try:
                    data = await att.read()
                except Exception:
                    continue
                txt = _ocr_text(data) or ""
                if any(k in (txt.lower()) for k in KEYWORDS):
                    try:
                        await delete_message_safe(message, actor="OCRGuard")
                    except Exception:
                        pass
                    try:
                        ch = await find_text_channel(self.bot, name="log-botphising")
                        if ch:
                            await ch.send(f"🖼️ [OCRGuard] Deleted {message.author.mention}'s image in {message.channel.mention} by OCR match")
                    except Exception:
                        pass
                    return
        except Exception:
            log.debug("OCRGuard error", exc_info=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(OCRGuard(bot))
