
import os
import json
from typing import List, Optional

import aiohttp
import discord
from discord.ext import commands
from discord import Thread, Message, Embed, Colour, AllowedMentions

from satpambot.bot.modules.discord_bot.helpers import img_hashing

TARGET_THREAD_NAME = os.getenv("SATPAMBOT_IMAGE_THREAD", "imagephising").lower()
PHASH_DB_TITLE = "SATPAMBOT_PHASH_DB_V1"
IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff", ".heic", ".heif")

def _is_image_attachment(att: discord.Attachment) -> bool:
    try:
        ct = (att.content_type or "").lower()
    except Exception:
        ct = ""
    if ct.startswith("image/"):
        return True
    fn = (att.filename or "").lower()
    return any(fn.endswith(x) for x in IMAGE_EXTS)

def _extract_hashes_from_msg(msg: Message) -> List[str]:
    if not msg or not msg.content:
        return []
    try:
        start = msg.content.find("{")
        end = msg.content.rfind("}")
        if start != -1 and end != -1 and end > start:
            j = json.loads(msg.content[start:end+1])
            if isinstance(j, dict) and "phash" in j and isinstance(j["phash"], list):
                uniq, seen = [], set()
                for h in j["phash"]:
                    s = str(h).strip()
                    if s and s not in seen:
                        seen.add(s); uniq.append(s)
                return uniq
    except Exception:
        pass
    return []

def _render_db_content(arr: List[str]) -> str:
    data = {"phash": arr}
    return f"{PHASH_DB_TITLE}\n```json\n{json.dumps(data, ensure_ascii=False)}\n```"

class PhishHashInbox(commands.Cog):
    """Watch a specific thread and register pHash values into a JSON message in the parent channel."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _find_db_message(self, channel: discord.TextChannel) -> Optional[Message]:
        async for m in channel.history(limit=100):
            if (m.content or "").startswith(PHASH_DB_TITLE):
                return m
        return None

    @commands.Cog.listener()
    async def on_message(self, message: Message):
        if message.author.bot or not message.attachments:
            return
        ch = message.channel
        if not isinstance(ch, Thread):
            return
        try:
            if (ch.name or "").lower() != TARGET_THREAD_NAME:
                return
        except Exception:
            return

        atts = [a for a in message.attachments if _is_image_attachment(a)]
        if not atts:
            return

        filenames: List[str] = []
        added_hashes: List[str] = []
        all_hashes: List[str] = []

        # load cfg defaults safely
        try:
            from satpambot.bot.modules.discord_bot.helpers import static_cfg
        except Exception:
            class static_cfg:
                PHASH_MAX_FRAMES = 6
                PHASH_AUGMENT_REGISTER = True
                PHASH_AUGMENT_PER_FRAME = 5

        async with aiohttp.ClientSession() as session:
            for att in atts:
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
                    filenames.append(att.filename or "file")

        if not all_hashes:
            return

        parent = ch.parent or ch
        db_msg = await self._find_db_message(parent)
        existing: List[str] = _extract_hashes_from_msg(db_msg) if db_msg else []
        existing_set = set(existing)
        for h in all_hashes:
            if h not in existing_set:
                existing.append(h)
                existing_set.add(h)
                added_hashes.append(h)

        try:
            content = _render_db_content(existing)
            if db_msg:
                await db_msg.edit(content=content, allowed_mentions=AllowedMentions.none())
            else:
                db_msg = await parent.send(content, allowed_mentions=AllowedMentions.none())
        except Exception:
            pass

        sample_hash = ", ".join(f"`{x[:16]}…`" for x in added_hashes[:3]) if added_hashes else "-"
        sample_file = ", ".join(f"`{x}`" for x in filenames[:3]) if filenames else "-"

        emb = discord.Embed(
            title="✅ Phish image registered",
            description=f"Gambar dari thread **{TARGET_THREAD_NAME}** berhasil diproses & didaftarkan.",
            colour=discord.Colour.green(),
        )
        emb.add_field(name="Files", value=str(len(filenames)), inline=True)
        emb.add_field(name="Hashes added", value=str(len(added_hashes)), inline=True)
        if sample_hash != "-":
            emb.add_field(name="Contoh Hash", value=sample_hash, inline=False)
        emb.add_field(name="Contoh File", value=sample_file, inline=False)
        emb.set_footer(text="SatpamBot • Inbox watcher")

        try:
            await message.reply(embed=emb, allowed_mentions=AllowedMentions.none())
        except Exception:
            pass

async def setup(bot: commands.Bot):
    await bot.add_cog(PhishHashInbox(bot))

def legacy_setup(bot: commands.Bot):
    bot.add_cog(PhishHashInbox(bot))
