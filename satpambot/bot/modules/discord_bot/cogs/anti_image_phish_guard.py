from __future__ import annotations

import io, json, os
from typing import List, Optional, Tuple

import discord
from discord.ext import commands, tasks
from PIL import Image
import imagehash

PHASH_DB_FILE = os.getenv("PHISH_IMG_DB", "data/phish_phash.json")
DASHBOARD_JSON = os.getenv("PHISH_DASHBOARD_JSON", "satpambot/dashboard/data/phash_index.json")
AUTOBAN_DEFAULT = True
THRESHOLD_DEFAULT = 8

INBOX_CHANNEL_ID = os.getenv("PHISH_INBOX_CHANNEL_ID") or os.getenv("STICKY_CHANNEL_ID") or os.getenv("LOG_CHANNEL_ID") or os.getenv("LOG_CHANNEL_ID_RAW")
INBOX_CHANNEL_ID = int(INBOX_CHANNEL_ID) if str(INBOX_CHANNEL_ID).isdigit() else None

PHASH_MARKER = "SATPAMBOT_PHASH_DB_V1"
POLICY_MARKER = "SATPAMBOT_PHASH_POLICY_V1"

def _load_json(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as f: return json.load(f)
    except Exception: return {}

def _union_hashes(existing: List[str], new: List[str]) -> List[str]:
    seen = set([h.lower() for h in existing if isinstance(h, str)]); out = [h.lower() for h in existing if isinstance(h, str)]
    for h in new:
        h = str(h).lower()
        if all(c in "0123456789abcdef" for c in h) and h not in seen:
            seen.add(h); out.append(h)
    return out

class AntiImagePhishGuard(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.phash_list: List[str] = []
        self.threshold = THRESHOLD_DEFAULT
        self.autoban = AUTOBAN_DEFAULT
        self._seen = set()
        self._refresh_task.start()

    def _load_local(self) -> Tuple[List[str], Optional[dict]]:
        lst = []
        j1 = _load_json(PHASH_DB_FILE); j2 = _load_json(DASHBOARD_JSON)
        if isinstance(j1, dict): lst = _union_hashes(lst, j1.get("phash", []))
        if isinstance(j2, dict): lst = _union_hashes(lst, j2.get("phash", []))
        pol = _load_json("data/phish_policy.json")
        return lst, pol if pol else None

    async def _read_pinned(self) -> Tuple[List[str], Optional[dict]]:
        lst, policy = [], None
        try:
            if not INBOX_CHANNEL_ID: return lst, None
            ch = self.bot.get_channel(INBOX_CHANNEL_ID) or await self.bot.fetch_channel(INBOX_CHANNEL_ID)
            pins = await ch.pins()
            for m in pins:
                if m.content and PHASH_MARKER in m.content:
                    try:
                        s = m.content.split("```json",1)[1].split("```",1)[0]; j = json.loads(s); lst = list(j.get("phash", []))
                    except Exception: pass
                if m.content and POLICY_MARKER in m.content:
                    try:
                        s = m.content.split("```json",1)[1].split("```",1)[0]; policy = json.loads(s)
                    except Exception: pass
        except Exception: pass
        return lst, policy

    async def _refresh_once(self):
        local, pol_file = self._load_local()
        pins, pol_pin = await self._read_pinned()
        self.phash_list = _union_hashes(local, pins)
        pol = pol_pin or pol_file or {}
        self.threshold = int(pol.get("threshold", THRESHOLD_DEFAULT))
        self.autoban = bool(pol.get("autoban", AUTOBAN_DEFAULT))

    @tasks.loop(minutes=1.0)
    async def _refresh_task(self): await self._refresh_once()

    @_refresh_task.before_loop
    async def _ready(self):
        await self.bot.wait_until_ready()
        await self._refresh_once()

    def _in_inbox(self, channel: discord.abc.GuildChannel | discord.Thread) -> bool:
        if not INBOX_CHANNEL_ID: return False
        if isinstance(channel, discord.TextChannel): return channel.id == INBOX_CHANNEL_ID
        if isinstance(channel, discord.Thread):
            try:
                name = (channel.name or "").lower()
                return channel.parent_id == INBOX_CHANNEL_ID and ("imagephish" in name or "imagephising" in name)
            except Exception: return False
        return False

    def _is_match(self, h: str) -> bool:
        try: h1 = int(h, 16)
        except Exception: return False
        for k in self.phash_list:
            try:
                if bin(int(k,16) ^ h1).count("1") <= self.threshold: return True
            except Exception: continue
        return False

    async def _hash_attachments(self, message: discord.Message) -> List[str]:
        out = []
        for att in message.attachments:
            try:
                if att.content_type and not att.content_type.startswith("image"): continue
                data = await att.read()
                img = Image.open(io.BytesIO(data)).convert("RGB")
                out.append(str(imagehash.phash(img)))
            except Exception: continue
        return out

    async def _maybe_ban(self, message: discord.Message, reason: str):
        try:
            if not self.autoban: return
            if not isinstance(message.author, discord.Member): return
            m = message.author
            if m.guild_permissions.manage_guild or m.guild_permissions.manage_messages or m.guild_permissions.administrator: return
            await message.guild.ban(m, reason=reason, delete_message_days=1)
            try: await message.channel.send(f"🚫 Auto-banned {m.mention} — {reason}", delete_after=5)
            except Exception: pass
        except Exception: pass

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild: return
        if not message.attachments: return
        if self._in_inbox(message.channel): return
        if message.id in self._seen: return
        self._seen.add(message.id)

        hashes = await self._hash_attachments(message)
        for h in hashes:
            if self._is_match(h):
                try: await message.add_reaction("⛔")
                except Exception: pass
                await self._maybe_ban(message, f"Detected phishing image (pHash match, thr={self.threshold})")
                break

async def setup(bot: commands.Bot):
    await bot.add_cog(AntiImagePhishGuard(bot))
