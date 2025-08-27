from __future__ import annotations

import asyncio, io, json, os
from typing import List

import discord
from discord.ext import commands
from PIL import Image
import imagehash

PHASH_DB_FILE = os.getenv("PHISH_IMG_DB", "data/phish_phash.json")
DASHBOARD_JSON = os.getenv("PHISH_DASHBOARD_JSON", "satpambot/dashboard/data/phash_index.json")

PHASH_INBOX_CHANNEL_ID = os.getenv("PHISH_INBOX_CHANNEL_ID") or os.getenv("STICKY_CHANNEL_ID") or os.getenv("LOG_CHANNEL_ID") or os.getenv("LOG_CHANNEL_ID_RAW")
PHASH_INBOX_CHANNEL_ID = int(PHASH_INBOX_CHANNEL_ID) if str(PHASH_INBOX_CHANNEL_ID).isdigit() else None

PHASH_MARKER = "SATPAMBOT_PHASH_DB_V1"

def _load_json(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _save_json(path: str, data: dict) -> None:
    from pathlib import Path
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

async def _write_pinned_json(bot: commands.Bot, payload: dict) -> None:
    try:
        if not PHASH_INBOX_CHANNEL_ID:
            return
        ch = bot.get_channel(PHASH_INBOX_CHANNEL_ID)
        if not isinstance(ch, discord.TextChannel):
            ch = await bot.fetch_channel(PHASH_INBOX_CHANNEL_ID)
            if not isinstance(ch, discord.TextChannel):
                return
        pins = await ch.pins()
        msg = None
        for m in pins:
            if m.author.id == bot.user.id and m.content and PHASH_MARKER in m.content:
                msg = m; break
        content = f"{PHASH_MARKER}\n```json\n{json.dumps(payload, ensure_ascii=False, separators=(',', ':'))}\n```"
        if msg: await msg.edit(content=content, allowed_mentions=discord.AllowedMentions.none())
        else:
            msg = await ch.send(content=content, allowed_mentions=discord.AllowedMentions.none())
            try: await msg.pin()
            except Exception: pass
    except Exception:
        pass

def _union_hashes(existing: List[str], new: List[str]) -> List[str]:
    seen = set(existing); out = list(existing)
    for h in new:
        h = str(h).lower()
        if all(c in "0123456789abcdef" for c in h) and h not in seen:
            seen.add(h); out.append(h)
    return out

class PhishHashInbox(commands.Cog):
    """Ingest images dropped into a channel/thread and persist their pHash.
    Only members with Manage Guild/Messages/Admin are allowed.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._lock = asyncio.Lock()

    def _has_perm(self, member: discord.Member) -> bool:
        try:
            return member.guild_permissions.manage_guild or member.guild_permissions.manage_messages or member.guild_permissions.administrator
        except Exception:
            return False

    async def _add_hashes(self, hashes: List[str]) -> int:
        j = _load_json(PHASH_DB_FILE); curr = j.get("phash", []) if isinstance(j, dict) else []
        new_list = _union_hashes(curr, hashes)
        if new_list != curr: _save_json(PHASH_DB_FILE, {"phash": new_list})

        k = _load_json(DASHBOARD_JSON); curr2 = k.get("phash", []) if isinstance(k, dict) else []
        new_list2 = _union_hashes(curr2, hashes)
        if new_list2 != curr2: _save_json(DASHBOARD_JSON, {"phash": new_list2})

        await _write_pinned_json(self.bot, {"phash": new_list2 or new_list})
        return len(new_list2 or new_list) - len(curr2 or curr)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Only watch configured channel or its threads (name contains 'imagephish'/'imagephising')
        if not PHASH_INBOX_CHANNEL_ID:
            return
        ch = message.channel; ok = False
        if isinstance(ch, discord.TextChannel) and ch.id == PHASH_INBOX_CHANNEL_ID: ok = True
        elif isinstance(ch, discord.Thread):
            try:
                name = (ch.name or "").lower()
                if ch.parent_id == PHASH_INBOX_CHANNEL_ID and ("imagephish" in name or "imagephising" in name):
                    ok = True
            except Exception: pass
        if not ok: return

        if message.author.bot or not message.attachments: return
        if not isinstance(message.author, discord.Member): return
        if not self._has_perm(message.author): return

        hashes: List[str] = []
        for att in message.attachments:
            if att.content_type and not att.content_type.startswith("image"): continue
            try:
                data = await att.read()
                img = Image.open(io.BytesIO(data)).convert("RGB")
                h = str(imagehash.phash(img)); hashes.append(h)
            except Exception: continue
        if not hashes: return

        async with self._lock: await self._add_hashes(hashes)
        try: await message.add_reaction("✅")
        except Exception: pass
        try: await message.reply(f"Ditambahkan {len(set(hashes))} hash.", mention_author=False, delete_after=10)
        except Exception: pass

async def setup(bot: commands.Bot):
    await bot.add_cog(PhishHashInbox(bot))
