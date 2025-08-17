from satpambot.bot.modules.discord_bot.utils.whitelist_guard import should_skip_moderation
from __future__ import annotations
import os, io, json
from pathlib import Path
from typing import List
import discord
from discord.ext import commands
from PIL import Image
import imagehash

from satpambot.bot.modules.discord_bot.utils.actions import delete_message_safe
from ..helpers.log_utils import find_text_channel

PHASH_FILE = Path(os.getenv("PHISH_PHASH_FILE") or "data/phish_phash.json")
PHASH_THRESH = 8)

def _load_hashes() -> List[imagehash.ImageHash]:
    try:
        data = json.loads(PHASH_FILE.read_text(encoding="utf-8"))
        return [imagehash.hex_to_hash(h) for h in data.get("phash",[])]
    except Exception:
        return []

def _ensure_db():
    if not PHASH_FILE.exists():
        PHASH_FILE.parent.mkdir(parents=True, exist_ok=True)
        PHASH_FILE.write_text(json.dumps({"phash":[]}, indent=2), encoding="utf-8")


def _append_recent_ban(user, guild):
    try:
        import json, os, time
        path = os.path.join("data","recent_bans.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        data = {"items":[]}
        if os.path.exists(path):
            try:
                data = json.load(open(path,"r",encoding="utf-8"))
            except Exception:
                data = {"items":[]}
        item = {
            "key": f"{getattr(guild,'id',0)}-{getattr(user,'id',user)}-{int(time.time())}",
            "ts": int(time.time()),
            "user_id": getattr(user,'id',user),
            "user_name": getattr(user,'name', str(user)),
            "guild_id": getattr(guild,'id',0),
            "guild_name": getattr(guild,'name',''),
        }
        data["items"] = (data.get("items",[]) + [item])[-100:]
        json.dump(data, open(path,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
    except Exception:
        pass

class AntiImagePhishSignature(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        _ensure_db()

    @commands.Cog.listener()
    \1
        try:
            if await should_skip_moderation(message):
                return
        except Exception:
            pass
if message.author.bot or not message.attachments:
            return
        try:
            imgs = [a for a in message.attachments if (a.content_type or "").startswith("image/")]
            if not imgs:
                return
            refs = _load_hashes()
            if not refs:
                return
            for att in imgs:
                if att.size and att.size > 4*1024*1024:
                    continue
                data = await att.read()
                try:
                    img = Image.open(io.BytesIO(data)).convert("RGB")
                    h = imagehash.phash(img)
                except Exception:
                    continue
                for r in refs:
                    if (h - r) <= PHASH_THRESH:
                        await delete_message_safe(message, actor="AntiImagePhish (signature)")
                        ch = await find_text_channel(self.bot, name="log-botphising")
                        if ch:
                            try:
                                # Reuse single thread
                                cfg = _cfg()
                                tname = cfg.get("log_thread_name","Ban Log")
                                target_thread = None
                                try:
                                    async for th in ch.threads(limit=50):
                                        if th.name == tname:
                                            target_thread = th; break
                                except Exception:
                                    pass
                                if not target_thread:
                                    try:
                                        target_thread = await ch.create_thread(name=tname, auto_archive_duration=1440, type=discord.ChannelType.public_thread)
                                    except Exception:
                                        target_thread = None
                                emb = discord.Embed(title="🚫 Phishing Image Detected (signature)")
                                emb.add_field(name="User", value=f"{message.author.mention} ({message.author.id})", inline=False)
                                emb.add_field(name="Channel", value=message.channel.mention, inline=False)
                                emb.add_field(name="Action", value="message deleted", inline=True)
                                await (target_thread.send(embed=emb) if target_thread else ch.send(embed=emb))
                            except Exception:
                                pass
                        if _cfg().get("autoban"):
                            try:
                                await message.guild.ban(message.author, reason="[auto] phishing image", delete_message_days=1)
                            _append_recent_ban(message.author, message.guild)
                            except Exception:
                                pass
                        return
        except Exception:
            pass

async def setup(bot): await bot.add_cog(AntiImagePhishSignature(bot))