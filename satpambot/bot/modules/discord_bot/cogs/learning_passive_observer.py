from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from collections import deque
from typing import Dict, Any, Deque, Set

import discord
from discord.ext import commands

LOGGER = logging.getLogger(__name__)

# --- Inline XP Rules (no ENV) ---
TK_TOTAL = 2000
L1_CUTOFF = 1000
L2_CUTOFF = 2000

# Channel guard (no XP here)
CHANNEL_BLOCKLIST = {
    1400375184048787566,
}

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "data")
STORE_PATH = os.path.join(DATA_DIR, "xp_store.json")
AWARDED_IDS_PATH = os.path.join(DATA_DIR, "xp_awarded_ids.json")

# Avoid runaway memory — persist awarded message ids with a ring buffer behavior
MAX_AWARDED_IDS = 50000

def _ensure_data_files():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(STORE_PATH):
        with open(STORE_PATH, "w", encoding="utf-8") as f:
            json.dump({}, f)
    if not os.path.exists(AWARDED_IDS_PATH):
        with open(AWARDED_IDS_PATH, "w", encoding="utf-8") as f:
            json.dump({"ids": []}, f)

def _load_store() -> Dict[str, Any]:
    _ensure_data_files()
    try:
        with open(STORE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _save_store(store: Dict[str, Any]):
    _ensure_data_files()
    tmp = STORE_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(store, f, ensure_ascii=False, indent=2)
    os.replace(tmp, STORE_PATH)

def _load_awarded_ids() -> Deque[int]:
    _ensure_data_files()
    try:
        with open(AWARDED_IDS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            ids = data.get("ids", [])
            dq: Deque[int] = deque(maxlen=MAX_AWARDED_IDS)
            for v in ids[-MAX_AWARDED_IDS:]:
                dq.append(v)
            return dq
    except Exception:
        return deque(maxlen=MAX_AWARDED_IDS)

def _save_awarded_ids(dq: Deque[int]):
    _ensure_data_files()
    tmp = AWARDED_IDS_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"ids": list(dq)}, f, ensure_ascii=False)
    os.replace(tmp, AWARDED_IDS_PATH)

def compute_level(total_xp: int) -> str:
    if total_xp < L1_CUTOFF:
        return "TK-L1"
    if total_xp < L2_CUTOFF:
        return "TK-L2"
    # Lewat TK -> anggap masuk SD-L1 untuk kompatibilitas ke depan
    return "SD-L1"

LOG_PATTERNS = [
    re.compile(r"^(INFO|WARNING|ERROR)\:"),        # log-style spam
    re.compile(r"loaded satpambot", re.IGNORECASE),
    re.compile(r"smoke_cogs\.py|smoke_lint_thread_guard\.py", re.IGNORECASE),
]

def _is_spam_like(content: str) -> bool:
    if not content:
        return False
    if len(content) > 2000 or content.count("\n") > 30:
        return True
    return any(p.search(content) for p in LOG_PATTERNS)

class LearningPassiveObserver(commands.Cog):
    """Passive XP earner (no ENV). Stores to data/xp_store.json and dedupes by message id.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.store: Dict[str, Any] = _load_store()
        self.awarded_ids: Deque[int] = _load_awarded_ids()
        # author cooldown: avoid +1 on rapid spam
        self.author_last_ts: Dict[int, float] = {}
        self.cooldown_sec = 5.0  # tweakable here (no ENV)

    def _user_key(self, guild_id: int, user_id: int) -> str:
        return f"{guild_id}:{user_id}"

    def _add_xp(self, guild_id: int, user_id: int, msg_id: int) -> None:
        key = self._user_key(guild_id, user_id)
        rec = self.store.get(key, {"xp": 0})
        rec["xp"] = int(rec.get("xp", 0)) + 1
        self.store[key] = rec
        self.awarded_ids.append(int(msg_id))
        _save_store(self.store)
        _save_awarded_ids(self.awarded_ids)
        level = compute_level(rec["xp"])
        LOGGER.info("[passive-learning] +1 XP -> total=%s level=%s", rec["xp"], level)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Skip bots / DMs / no content
        if message.author.bot or not message.guild:
            return
        if message.channel.id in CHANNEL_BLOCKLIST:
            return
        if _is_spam_like(message.content or ""):
            return

        # Dedup by message id if we've already awarded
        mid = int(message.id)
        if mid in self.awarded_ids:
            return

        # Simple per-author cooldown to reduce +1 spam storms
        ts = message.created_at.timestamp() if message.created_at else 0.0
        last = self.author_last_ts.get(message.author.id, 0.0)
        if ts and last and (ts - last) < self.cooldown_sec:
            return
        self.author_last_ts[message.author.id] = ts or last

        # Award
        try:
            self._add_xp(message.guild.id, message.author.id, mid)
        except Exception as e:
            LOGGER.exception("XP award failed: %s", e)

async def setup(bot: commands.Bot):
    await bot.add_cog(LearningPassiveObserver(bot))
