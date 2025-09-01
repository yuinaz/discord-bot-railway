
import json
import aiohttp
import discord
from discord.ext import commands
from discord import Thread, Message, AllowedMentions

# use helpers already in project; DO NOT change config file
from satpambot.bot.modules.discord_bot.helpers import img_hashing, static_cfg

PHASH_DB_TITLE = "SATPAMBOT_PHASH_DB_V1"
TARGET_THREAD_NAME = getattr(static_cfg, "PHISH_INBOX_THREAD", "imagephising").lower()
IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff")

def _is_image_attachment(att: discord.Attachment) -> bool:
    ct = (att.content_type or "").lower() if hasattr(att, "content_type") else ""
    if ct.startswith("image/"):
        return True
    fn = (att.filename or "").lower()
    return any(fn.endswith(x) for x in IMAGE_EXTS)

def _render_db(phashes):
    data = {"phash": phashes}
    return f"{PHASH_DB_TITLE}\n```json\n{json.dumps(data, ensure_ascii=False)}\n```"

def _extract_hashes_from_json_msg(msg: discord.Message):
    if not msg or not msg.content:
        return []
    s = msg.content
    i, j = s.find("{"), s.rfind("}")
    if i != -1 and j != -1 and j > i:
        try:
            obj = json.loads(s[i:j+1])
            arr = obj.get("phash", [])
            return [str(x).strip() for x in arr if str(x).strip()]
        except Exception:
            return []
    return []

class PhishHashInbox(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _find_db_message(self, channel: discord.TextChannel):
        async for m in channel.history(limit=200):
            if (m.content or "").startswith(PHASH_DB_TITLE):
                return m
        return None

    @commands.Cog.listener()
    async def on_message(self, message: Message):
        # only react to attachments in the target inbox thread
        if message.author.bot or not message.attachments:
            return
        ch = message.channel
        if not isinstance(ch, Thread):
            return
        if (ch.name or "").lower() != TARGET_THREAD_NAME:
            return

        # compute multi-frame hashes per attachment
        all_hashes, filenames = [], []
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
                    filenames.append(att.filename or "file")

        if not all_hashes:
            return

        parent = ch.parent or ch
        db_msg = await self._find_db_message(parent)
        existing = _extract_hashes_from_json_msg(db_msg) if db_msg else []
        existing_set = set(existing)
        added = []
        for h in all_hashes:
            if h not in existing_set:
                existing.append(h)
                existing_set.add(h)
                added.append(h)

        # write back to channel JSON message (persist on Discord)
        try:
            content = _render_db(existing)
            if db_msg:
                await db_msg.edit(content=content, allowed_mentions=AllowedMentions.none())
            else:
                await parent.send(content, allowed_mentions=AllowedMentions.none())
        except Exception:
            pass

        # send summary EMBED to **parent channel** (not thread)
        try:
            e = discord.Embed(
                title="✅ Phish image registered",
                description=f"Gambar dari thread **{TARGET_THREAD_NAME}** berhasil diproses & didaftarkan.",
                colour=discord.Colour.green(),
            )
            e.add_field(name="Files", value=str(len(filenames)), inline=True)
            e.add_field(name="Hashes added", value=str(len(added)), inline=True)
            if added:
                sample = ", ".join(f"`{h[:16]}…`" for h in added[:3])
                e.add_field(name="Contoh Hash", value=sample, inline=False)
            if filenames:
                e.add_field(name="Contoh File", value=", ".join(f"`{f}`" for f in filenames[:3]), inline=False)
            e.set_footer(text="SatpamBot • Inbox watcher")
            await parent.send(embed=e, allowed_mentions=AllowedMentions.none())
        except Exception:
            pass

async def setup(bot: commands.Bot):
    await bot.add_cog(PhishHashInbox(bot))

def legacy_setup(bot: commands.Bot):
    bot.add_cog(PhishHashInbox(bot))
