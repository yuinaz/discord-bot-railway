
from __future__ import annotations
"""
anti_image_phish_advanced.py — speed-boosted + icon mode
- Skip heavy analysis for command messages (prefix/"/")
- Use async cached poster or small icon from helpers.ban_poster
- Do ban & delete while poster/icon processed in background
"""
import os, re, asyncio
from typing import Optional, List, Dict

import discord
from discord.ext import commands
from modules.discord_bot.utils.actions import delete_message_safe

try:
    try:
    # prefer helper jika ada
    from modules.discord_bot.helpers.ban_poster import (
        render_to_buffer_async, poster_enabled, poster_icon_mode, load_icon_bytes
    )
except Exception:
    # fallback: pakai cogs.image_poster (build_poster) kalau helpers tidak ada
    try:
        from modules.discord_bot.cogs.image_poster import build_poster as _build_poster  # type: ignore

        async def render_to_buffer_async(username: str, mode: str = "ban"):
            try:
                return _build_poster(username, mode=mode)  # returns BytesIO or None
            except Exception:
                return None

        def poster_enabled() -> bool: return True
        def poster_icon_mode() -> bool: return False
        def load_icon_bytes(size: int = 192): return None
    except Exception:
        async def render_to_buffer_async(username: str, mode: str = "ban"): return None
        def poster_enabled() -> bool: return False
        def poster_icon_mode() -> bool: return False
        def load_icon_bytes(size: int = 192): return None
except Exception:
    async def render_to_buffer_async(username: str, mode: str="ban"): return None
    def poster_enabled(): return False
    def poster_icon_mode(): return False
    def load_icon_bytes(size: int = 192): return None

URL_RE = re.compile(r"https?://[^\s>)+\"']+", re.I)

class AntiImagePhishAdvanced(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.log_channel_name = os.getenv("LOG_CHANNEL_NAME", "log-botphishing")
        self.prefix = os.getenv("BOT_PREFIX", "!")
        self.delete_secs = min(int(os.getenv("PHISH_BAN_DELETE_SECONDS", str(7*24*3600))), 7*24*3600)

    async def _ban(self, message: discord.Message, reason: str) -> bool:
        m = message.author
        if not isinstance(m, discord.Member): return False
        try:
            await message.guild.ban(m, reason=reason, delete_message_seconds=self.delete_secs)
            return True
        except Exception:
            return False

    async def _log_simple(self, message: discord.Message, text: str):
        ch = None
        raw = os.getenv("LOG_CHANNEL_ID")
        if raw and raw.isdigit():
            ch = message.guild.get_channel(int(raw))
        if not ch:
            ch = discord.utils.get(message.guild.text_channels, name=self.log_channel_name) or message.channel
        try:
            await ch.send(text)
        except Exception:
            pass

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        content = message.content or ""
        stripped = content.lstrip()
        if stripped.startswith(self.prefix) or stripped.startswith("/"):
            return
        if not (message.attachments or URL_RE.search(content) or message.mention_everyone):
            return
        analyze = getattr(self, "analyze", None)
        if not analyze:
            return
        v = await analyze(message)

        is_hard = (v.get("nsfw_level") == "hard") or (v.get("adult_link") == "hard") or v.get("bad")
        is_soft = (v.get("nsfw_level") == "soft") or (v.get("adult_link") == "soft")

        if is_hard:
            poster_task = None
            icon_buf = None
            if poster_enabled():
                if poster_icon_mode():
                    icon_buf = load_icon_bytes(160)  # small icon
                else:
                    username = getattr(message.author, "display_name", str(message.author))
                    poster_task = asyncio.create_task(render_to_buffer_async(username, mode="ban"))
            await delete_message_safe(message, actor='anti_image_phish_advanced')
except Exception: pass
            ok = await self._ban(message, "Hard NSFW/Phishing/Abuse detected")
            await self._log_simple(message, f"⛔ Auto-ban {message.author.mention} (hard)")
            # send poster/icon
            try:
                if icon_buf is not None:
                    file = discord.File(icon_buf, filename="fibi_icon.png")
                    embed = discord.Embed(colour=discord.Colour.red(), title="User diban otomatis")
                    embed.set_thumbnail(url="attachment://fibi_icon.png")
                    await message.channel.send(file=file, embed=embed)
                elif poster_task:
                    buf = await poster_task
                    if buf is not None:
                        file = discord.File(buf, filename="ban_card.png")
                        embed = discord.Embed(colour=discord.Colour.red())
                        embed.set_image(url="attachment://ban_card.png")
                        await message.channel.send(file=file, embed=embed)
            except Exception:
                pass
            return

        if is_soft:
            await self._log_simple(message, f"ℹ️ Soft content detected for {message.author.mention} (ignored)")
            return


from discord.ext import commands as _commands_setup_patch
async def setup(bot: _commands_setup_patch.Bot):
    await bot.add_cog(AntiImagePhishAdvanced(bot))
