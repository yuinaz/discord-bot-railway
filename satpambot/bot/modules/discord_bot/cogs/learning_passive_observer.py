
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from collections import deque
from typing import Dict, Any, Deque

import discord
from discord.ext import commands

LOGGER = logging.getLogger(__name__)

L1_CUTOFF = 1000
L2_CUTOFF = 2000

CHANNEL_BLOCKLIST = {
    1400375184048787566,
}

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "data")
STORE_PATH = os.path.join(DATA_DIR, "xp_store.json")
AWARDED_IDS_PATH = os.path.join(DATA_DIR, "xp_awarded_ids.json")

MAX_AWARDED_IDS = 50000

def _ensure_data_files():
    os.makedirs(os.path.dirname(STORE_PATH), exist_ok=True)
    if not os.path.exists(STORE_PATH):
        with open(STORE_PATH, "w", encoding="utf-8") as f:
            json.dump({}, f, ensure_ascii=False, indent=2)
    if not os.path.exists(AWARDED_IDS_PATH):
        with open(AWARDED_IDS_PATH, "w", encoding="utf-8") as f:
            json.dump({"ids": []}, f, ensure_ascii=False, indent=2)

def _load_store() -> Dict[str, Any]:
    _ensure_data_files()
    try:
        with open(STORE_PATH, "r", encoding="utf-8") as f:
            return json.load(f) or {}
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

def _current_group(bot) -> str:
    override = os.getenv("LEARNING_FORCE_GROUP")
    if override:
        return override.lower()
    phase = (getattr(bot, "learning_phase", None) or os.getenv("LEARNING_FORCE_PHASE") or "TK").lower()
    return "senior" if phase == "senior" else "junior"

LADDER_JSON_PATH = os.getenv("LADDER_JSON_PATH", os.path.join(DATA_DIR, "ladder.json"))

try:
    from satpambot.bot.modules.discord_bot.helpers.ladder_utils import load_ladder, compute_label_from_group
except Exception:
    try:
        from ..helpers.ladder_utils import load_ladder, compute_label_from_group  # type: ignore
    except Exception:
        load_ladder = compute_label_from_group = None  # type: ignore

class LearningPassiveObserver(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.store: Dict[str, Any] = _load_store()
        self.awarded_ids: Deque[int] = _load_awarded_ids()
        self._ladder_map: Dict = {}
        if callable(load_ladder):
            self._ladder_map = load_ladder(LADDER_JSON_PATH) or {}
            if self._ladder_map:
                LOGGER.info("[learning-passive] ladder loaded: %s", LADDER_JSON_PATH)
            else:
                LOGGER.warning("[learning-passive] ladder empty or missing: %s", LADDER_JSON_PATH)

    def _key(self, gid: int, uid: int) -> str:
        return f"{gid}:{uid}"

    def _get_rec(self, gid: int, uid: int) -> Dict[str, Any]:
        return self.store.setdefault(self._key(gid, uid), {"xp": 0})

    def _compute_level_label(self, total_xp: int) -> str:
        group = _current_group(self.bot)
        if callable(compute_label_from_group) and self._ladder_map:
            label = compute_label_from_group(total_xp, group, self._ladder_map)
            if label:
                return label
        if total_xp < L1_CUTOFF: return "TK-L1"
        if total_xp < L2_CUTOFF: return "TK-L2"
        return "SD-L1"

    def _add_xp(self, gid: int, uid: int, mid: int) -> None:
        rec = self._get_rec(gid, uid)
        if mid in self.awarded_ids:
            return
        rec["xp"] = rec.get("xp", 0) + 1
        self.awarded_ids.append(mid)
        self.store[self._key(gid, uid)] = rec
        _save_store(self.store)
        _save_awarded_ids(self.awarded_ids)

        level = self._compute_level_label(rec["xp"])
        LOGGER.info("[passive-learning] +1 XP -> total=%s level=%s", rec["xp"], level)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild or not message.content:
            return
        if message.channel and message.channel.id in CHANNEL_BLOCKLIST:
            return
        try:
            self._add_xp(message.guild.id, message.author.id, message.id)
        except Exception as e:
            LOGGER.warning("[passive-learning] error: %r", e)
