\
# satpambot/bot/modules/discord_bot/cogs/reaction_allowlist_static.py
"""
Guard statis (tanpa ENV) untuk reaction ✅:
- Pertahankan ✅ hanya di channel/thread dengan NAMA yang cocok pola tertentu
  ATAU ID yang ditulis di konstanta di bawah.
- Tidak mengubah cogs lain; hanya menghapus ✅ yang ditambahkan BOT di tempat yang tidak diizinkan.
Edit konstanta di bawah jika perlu.
"""
import re
import logging
from typing import Set, List

import discord
from discord.ext import commands

log = logging.getLogger(__name__)

# ====== KONFIGURASI STATIS (boleh kamu edit di file ini) ======
# Emoji yang dijaga
EMOJIS_TO_GUARD: Set[str] = {"✅"}

# Nama channel/thread yang diizinkan (match case-insensitive, gunakan regex raw string)
ALLOWED_NAME_PATTERNS: List[str] = [
    r"image.?phish(ing)?",     # "imagephish", "image-phishing", dsb
    r"anti.?image.?phish(ing)?",
    r"phish(ing)?[-_ ]?images?",
]

# (Opsional) ID channel/thread yang diizinkan; kosongkan jika tidak perlu
ALLOWED_IDS: Set[int] = set()
# ===============================================================

def _is_name_allowed(name: str) -> bool:
    name_l = (name or "").lower()
    for pat in ALLOWED_NAME_PATTERNS:
        if re.search(pat, name_l):
            return True
    return False

class ReactionAllowlistStatic(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        log.info("[reaction-allowlist-static] active; patterns=%s ids=%s", ALLOWED_NAME_PATTERNS, sorted(ALLOWED_IDS) if ALLOWED_IDS else [])

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        # Hanya jaga emoji tertentu
        emoji_str = str(payload.emoji)
        if emoji_str not in EMOJIS_TO_GUARD:
            return
        # Hanya bertindak jika reaction dari bot sendiri (biar tidak ganggu user)
        if not self.bot.user or payload.user_id != self.bot.user.id:
            return
        # Ambil channel
        try:
            ch = self.bot.get_channel(payload.channel_id) or await self.bot.fetch_channel(payload.channel_id)
        except Exception:
            return
        # Cek allowlist
        allowed = False
        if payload.channel_id in ALLOWED_IDS:
            allowed = True
        else:
            # cek nama channel/thread
            ch_name = getattr(ch, "name", "") or getattr(getattr(ch, "parent", None), "name", "")
            if _is_name_allowed(ch_name):
                allowed = True
        if allowed:
            return  # biarkan ✅
        # Tidak diizinkan -> hapus ✅ milik bot
        try:
            msg = await ch.fetch_message(payload.message_id)
            await msg.remove_reaction(payload.emoji, self.bot.user)
        except Exception as e:
            log.warning("[reaction-allowlist-static] remove failed: %r", e)

async def setup(bot: commands.Bot):
    await bot.add_cog(ReactionAllowlistStatic(bot))
