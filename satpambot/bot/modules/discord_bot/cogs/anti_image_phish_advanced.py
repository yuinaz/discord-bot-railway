from satpambot.bot.modules.discord_bot.utils.whitelist_guard import should_skip_moderation
from __future__ import annotations
import logging, io, re
from typing import Optional
import discord
from discord.ext import commands

from satpambot.bot.modules.discord_bot.utils.actions import delete_message_safe
from ..helpers.log_utils import find_text_channel

log = logging.getLogger(__name__)

OCR_WORDS = {
    "verify","nitro","free","gift","login","claim","kode","otp","security",
    "appeal","banned","suspend","reward","airdrop","wallet"
}
URL_RX = re.compile(r"https?://[^\s>]+", re.I)

def _has_suspicious_words(text: str) -> bool:
    t = (text or "").lower()
    return any(w in t for w in OCR_WORDS)

def _ocr_extract_text(data: bytes) -> Optional[str]:
    # Optional OCR using pytesseract + PIL if available
    try:
        from PIL import Image
        import pytesseract
        with Image.open(io.BytesIO(data)) as im:
            im = im.convert("RGB")
            txt = pytesseract.image_to_string(im)
            return txt
    except Exception:
        return None

class AntiImagePhishAdvanced(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    \1
        try:
            if await should_skip_moderation(message):
                return
        except Exception:
            pass
try:
            if not message.guild or getattr(message.author, "bot", False):
                return
            atts = getattr(message, "attachments", []) or []
            if not atts:
                return
            # quick path: if caption contains link + keyword, act immediately
            caption = getattr(message, "content", "") or ""
            if URL_RX.search(caption) and _has_suspicious_words(caption):
                await delete_message_safe(message, actor="AntiImagePhish")
                ch = await find_text_channel(self.bot, name="log-botphising")
                if ch:
                    await ch.send(f"🧹 [AntiImagePhish] Deleted suspicious image post by {message.author.mention} (caption match)")
                return
            # OCR each attachment (only small ones)
            for att in atts:
                if not (att.content_type or "").startswith("image"):
                    continue
                if att.size and att.size > 4 * 1024 * 1024:  # skip >4MB
                    continue
                try:
                    data = await att.read()
                except Exception:
                    continue
                txt = _ocr_extract_text(data)
                if txt and _has_suspicious_words(txt):
                    await delete_message_safe(message, actor="AntiImagePhish (OCR)")
                    ch = await find_text_channel(self.bot, name="log-botphising")
                    if ch:
                        await ch.send(f"🧹 [AntiImagePhish] Deleted by OCR match for {message.author.mention} in {message.channel.mention}")
                    return
        except Exception:
            log.debug("AntiImagePhish handler failed", exc_info=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(AntiImagePhishAdvanced(bot))
