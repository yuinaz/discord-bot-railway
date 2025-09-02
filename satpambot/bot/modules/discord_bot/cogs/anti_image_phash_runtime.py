
from __future__ import annotations
import os, json, asyncio, aiohttp
from typing import Optional, Set

import discord
from discord.ext import commands

from satpambot.bot.modules.discord_bot.helpers import static_cfg, img_hashing

PHASH_DB_TITLE = "SATPAMBOT_PHASH_DB_V1"
IMAGE_EXTS = (".png",".jpg",".jpeg",".webp",".gif",".bmp",".tif",".tiff",".heic",".heif")
TARGET_INBOX = getattr(static_cfg, "PHISH_INBOX_THREAD", "imagephising").lower()

def _is_image_attachment(att: discord.Attachment) -> bool:
    ct = (att.content_type or "").lower() if hasattr(att, "content_type") else ""
    if ct.startswith("image/"):
        return True
    fn = (att.filename or "").lower()
    return any(fn.endswith(x) for x in IMAGE_EXTS)

class AntiImagePhashRuntime(commands.Cog):
    """Instant remove+ban when attachment pHash matches known phishing hashes.
    This cog does NOT change configs. It skips the inbox thread on purpose.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._phash_set: Set[str] = set()
        self._reload_lock = asyncio.Lock()

    async def _get_log_channel(self, guild: discord.Guild) -> Optional[discord.TextChannel]:
        cname = getattr(static_cfg, "LOG_CHANNEL_NAME", "log-botphising")
        ch = discord.utils.get(guild.text_channels, name=cname)
        return ch or guild.system_channel

    async def _load_phash_db(self) -> None:
        if self._reload_lock.locked():
            return
        async with self._reload_lock:
            s = set()
            try:
                for g in getattr(self.bot, "guilds", []):
                    ch = await self._get_log_channel(g)
                    if not ch:
                        continue
                    async for m in ch.history(limit=200):
                        if (m.content or "").startswith(PHASH_DB_TITLE):
                            cont = m.content or ""
                            i, j = cont.find("{"), cont.rfind("}")
                            if i != -1 and j != -1 and j > i:
                                try:
                                    data = json.loads(cont[i:j+1])
                                    arr = data.get("phash", [])
                                    for x in arr:
                                        x = str(x).strip()
                                        if x:
                                            s.add(x)
                                except Exception:
                                    pass
                            break
            except Exception:
                pass
            if s:
                self._phash_set = s

    @commands.Cog.listener()
    async def on_ready(self):
        await self._load_phash_db()

    @commands.Cog.listener()
    async def on_guild_available(self, guild: discord.Guild):
        await self._load_phash_db()

    async def _should_exempt(self, message: discord.Message) -> bool:
        # channels
        try:
            ex_channels = set(map(str.lower, getattr(static_cfg, "PHISH_EXEMPT_CHANNELS", "").split(",")))
            if message.channel and getattr(message.channel, "name", None):
                if message.channel.name.lower() in ex_channels:
                    return True
        except Exception:
            pass
        # roles
        try:
            ex_roles = set(map(str.lower, getattr(static_cfg, "PHISH_EXEMPT_ROLES", "").split(",")))
            roles = [r.name.lower() for r in getattr(message.author, "roles", []) if getattr(r, "name", None)]
            if ex_roles and any(r in ex_roles for r in roles):
                return True
        except Exception:
            pass
        return False

    async def _ban_author(self, message: discord.Message, reason: str):
        try:
            delete_days = int(os.getenv("PHISH_BAN_DELETE_DAYS", "7"))
        except Exception:
            delete_days = 7
        try:
            await message.guild.ban(message.author, reason=reason, delete_message_days=max(0, min(7, delete_days)))
        except Exception:
            try:
                await message.guild.kick(message.author, reason=reason)
            except Exception:
                pass

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.guild is None or message.author.bot:
            return
        # skip inbox thread
        ch = message.channel
        if isinstance(ch, discord.Thread):
            try:
                if (ch.name or "").lower() == TARGET_INBOX:
                    return
            except Exception:
                pass
        if await self._should_exempt(message):
            return
        if not message.attachments:
            return

        # compute pHash list
        all_hashes = []
        async with aiohttp.ClientSession() as session:
            for att in message.attachments:
                if not _is_image_attachment(att):
                    continue
                try:
                    async with session.get(att.url) as r:
                        raw = await r.read()
                except Exception:
                    continue
                hs = img_hashing.phash_list_from_bytes(
                    raw,
                    max_frames=getattr(static_cfg, "PHASH_MAX_FRAMES", 6),
                    augment=getattr(static_cfg, "PHASH_AUGMENT_REGISTER", True),
                    augment_per_frame=getattr(static_cfg, "PHASH_AUGMENT_PER_FRAME", 5),
                )
                if hs:
                    all_hashes.extend(hs)

        if not all_hashes or not self._phash_set:
            return

        # match and act
        for h in all_hashes:
            if h in self._phash_set:
                try:
                    await message.delete()
                except Exception:
                    pass
                await self._ban_author(message, "Phishing image (pHash match)")
                return

async def setup(bot: commands.Bot):
    await bot.add_cog(AntiImagePhashRuntime(bot))
