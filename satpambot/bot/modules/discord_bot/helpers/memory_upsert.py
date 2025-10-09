# -*- coding: utf-8 -*-
from __future__ import annotations
import json, logging, re
from typing import Any, Dict
import discord

from satpambot.bot.modules.discord_bot.config.self_learning_cfg import (
    LOG_CHANNEL_ID, NEURO_THREAD_ID, NEURO_THREAD_NAME, MEMORY_TITLE
)

log = logging.getLogger(__name__)

def _ensure_json(obj: Any) -> str:
    return "```json\n" + json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2) + "\n```"

def _deep_merge(dst: Dict, src: Dict) -> Dict:
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            _deep_merge(dst[k], v)
        else:
            dst[k] = v
    return dst

async def _find_by_name(bot: discord.Client, name_lower: str) -> discord.Thread | None:
    # Prefer in LOG channel if known
    if LOG_CHANNEL_ID:
        ch = bot.get_channel(LOG_CHANNEL_ID)
        if hasattr(ch, "threads"):
            for th in ch.threads:
                if isinstance(th, discord.Thread) and th.name.lower() == name_lower:
                    return th
        try:
            async for th in ch.archived_threads(limit=50):  # type: ignore
                if th.name.lower() == name_lower:
                    return th
        except Exception:
            pass
    # Fallback: scan guilds
    for g in bot.guilds:
        for ch in g.text_channels:
            for th in ch.threads:
                if th.name.lower() == name_lower:
                    return th
    return None

async def find_neuro_thread(bot: discord.Client) -> discord.Thread | None:
    if NEURO_THREAD_ID:
        t = bot.get_channel(NEURO_THREAD_ID)
        if isinstance(t, discord.Thread):
            return t
    return await _find_by_name(bot, NEURO_THREAD_NAME.lower())

async def upsert_pinned_memory(bot: discord.Client, patch: Dict[str, Any]) -> bool:
    th = await find_neuro_thread(bot)
    if not isinstance(th, discord.Thread):
        log.warning("[memory_upsert] neuro thread tidak ditemukan")
        return False

    # Cari keeper milik bot yang memuat MEMORY_TITLE
    keeper = None
    try:
        pins = await th.pins()
        for m in pins:
            if m.author == bot.user and MEMORY_TITLE in (m.content or ""):
                keeper = m
                break
    except Exception:
        pass
    if not keeper:
        async for m in th.history(limit=50, oldest_first=False):
            if m.author == bot.user and MEMORY_TITLE in (m.content or ""):
                keeper = m
                break

    base = {"lingo":{}, "threat_intel":{}}
    if keeper:
        match = re.search(r"```json\n(.*)\n```", keeper.content or "", flags=re.S)
        if match:
            try:
                base = json.loads(match.group(1)) or base
            except Exception:
                pass

    merged = _deep_merge(base, patch)
    body = f"**{MEMORY_TITLE}**\n" + _ensure_json(merged)

    if keeper:
        if keeper.content != body:
            await keeper.edit(content=body)
            log.info("[memory_upsert] keeper updated")
    else:
        keeper = await th.send(body)
        try:
            await keeper.pin()
        except Exception:
            pass
        log.info("[memory_upsert] keeper created & pinned")

    return True
