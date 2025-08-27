
import os
import json
import tempfile
from typing import List

import aiohttp
import discord
from discord.ext import commands
from discord import Thread, Message, Embed, Colour, AllowedMentions, File

TARGET_THREAD_NAME = os.getenv("SATPAMBOT_IMAGE_THREAD", "imagephising").lower()
DASHBOARD_BASE = os.getenv("SATPAMBOT_DASHBOARD_URL", "http://127.0.0.1:10000").rstrip("/")
PHASH_API = f"{DASHBOARD_BASE}/api/phish/phash"

IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff", ".heic", ".heif")

def _is_image_attachment(att: discord.Attachment) -> bool:
    ct = (att.content_type or "").lower()
    if ct.startswith("image/"):
        return True
    fname = (att.filename or "").lower()
    return any(fname.endswith(ext) for ext in IMAGE_EXTS)

def _extract_hashes(payload) -> List[str]:
    hashes = []
    try:
        if isinstance(payload, dict):
            if isinstance(payload.get("added"), list):
                hashes.extend([str(x) for x in payload["added"]])
            if isinstance(payload.get("hashes"), list):
                hashes.extend([str(x) for x in payload["hashes"]])
            if isinstance(payload.get("phash"), list):
                hashes.extend([str(x) for x in payload["phash"]])
            for k in ("phash", "hash"):
                v = payload.get(k)
                if isinstance(v, str):
                    hashes.append(v)
    except Exception:
        pass
    uniq, seen = [], set()
    for h in hashes:
        k = h.strip()
        if k and k not in seen:
            seen.add(k); uniq.append(k)
    return uniq

class PhishHashInbox(commands.Cog):
    """Watch thread 'imagephising', register pHash via dashboard API, and notify parent channel with SPOILER JSON."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

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

        parent = ch.parent or ch

        added_hashes: List[str] = []
        filenames: List[str] = []
        async with aiohttp.ClientSession() as session:
            for att in message.attachments:
                if not _is_image_attachment(att):
                    continue
                filenames.append(att.filename or "image")
                try:
                    data = await att.read()
                    if not data:
                        continue
                    fd = aiohttp.FormData()
                    fd.add_field("file", data, filename=att.filename or "image",
                                 content_type=att.content_type or "application/octet-stream")
                    async with session.post(PHASH_API, data=fd, timeout=aiohttp.ClientTimeout(total=45)) as resp:
                        payload = None
                        try:
                            payload = await resp.json()
                        except Exception:
                            payload = None
                        added_hashes.extend(_extract_hashes(payload))
                except Exception:
                    continue

        if not (filenames or added_hashes):
            return

        sample_hash = ", ".join(f"`{x[:16]}…`" for x in added_hashes[:3]) if added_hashes else "-"
        sample_file = ", ".join(f"`{x}`" for x in filenames[:3]) if filenames else "-"

        emb = Embed(
            title="✅ Phish image registered",
            description="Gambar dari thread **imagephising** berhasil diproses & didaftarkan.",
            colour=Colour.green(),
        )
        emb.add_field(name="Files", value=str(len(filenames)), inline=True)
        emb.add_field(name="Hashes added", value=str(len(added_hashes)), inline=True)
        if sample_hash != "-":
            emb.add_field(name="Contoh Hash", value=sample_hash, inline=False)
        emb.add_field(name="Contoh File", value=sample_file, inline=False)
        emb.set_footer(text="SatpamBot • Inbox watcher")

        file_arg = None; tmp_path = None
        if added_hashes:
            try:
                with tempfile.NamedTemporaryFile("w+", encoding="utf-8", suffix=".json", delete=False) as tf:
                    json.dump({"added": added_hashes}, tf, ensure_ascii=False, indent=2)
                    tmp_path = tf.name
                file_arg = File(tmp_path, filename="SPOILER_phash_added.json", spoiler=True)
            except Exception:
                file_arg = None

        try:
            await parent.send(embed=emb, file=file_arg, allowed_mentions=AllowedMentions.none())
        except Exception:
            pass
        finally:
            if tmp_path:
                try: os.remove(tmp_path)
                except Exception: pass

async def setup(bot: commands.Bot):
    await bot.add_cog(PhishHashInbox(bot))

def legacy_setup(bot: commands.Bot):
    bot.add_cog(PhishHashInbox(bot))
