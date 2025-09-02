# -*- coding: utf-8 -*-
"""
helpers/memory_wb.py
- Membuat / mendapatkan thread "memory W*B" di channel log (ID > NAME fallback).
- Menaruh embed ringkasan + lampiran whitelist.txt, blacklist.txt (mirror).
- Menyimpan state ID pesan di data/memory_wb.json agar update berikutnya edit, bukan spam.
"""
from __future__ import annotations
import os, json, io
from pathlib import Path
from typing import Iterable, Optional

import discord

LOG_CHANNEL_NAME = os.getenv("LOG_CHANNEL_NAME", "log-botphising")
LOG_CHANNEL_ID_RAW = os.getenv("LOG_CHANNEL_ID", "").strip()
MEMORY_THREAD_NAME = os.getenv("MEMORY_WB_THREAD_NAME", "memory W*B")
STATE_FILE = Path("data/memory_wb.json")

async def _resolve_log_channel(bot: discord.Client) -> Optional[discord.TextChannel]:
    chan_id = int(LOG_CHANNEL_ID_RAW) if LOG_CHANNEL_ID_RAW.isdigit() else None
    for guild in bot.guilds:
        if chan_id:
            ch = guild.get_channel(chan_id) or discord.utils.get(guild.text_channels, id=chan_id)
            if isinstance(ch, discord.TextChannel):
                return ch
        ch = discord.utils.find(lambda c: isinstance(c, discord.TextChannel) and c.name == LOG_CHANNEL_NAME, guild.text_channels)
        if ch:
            return ch
    return None

async def ensure_memory_thread(bot: discord.Client) -> Optional[discord.Thread]:
    ch = await _resolve_log_channel(bot)
    if not ch:
        return None
    for th in ch.threads:
        if (th.name or "").lower() == MEMORY_THREAD_NAME.lower():
            return th
    try:
        archived = await ch.archived_threads(limit=50).flatten()
        for th in archived:
            if (th.name or "").lower() == MEMORY_THREAD_NAME.lower():
                await th.unarchive()
                return th
    except Exception:
        pass
    try:
        return await ch.create_thread(name=MEMORY_THREAD_NAME)
    except Exception:
        return None

def _read_state():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}

def _write_state(d: dict):
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass

def _txt_file(name: str, items: Iterable[str]) -> discord.File:
    text = "\n".join(sorted({str(x).strip() for x in items if str(x).strip()}))
    import io as _io
    bio = _io.BytesIO(text.encode("utf-8"))
    return discord.File(bio, filename=name)

async def update_memory_wb(bot: discord.Client, wl: Iterable[str], bl: Iterable[str]) -> None:
    th = await ensure_memory_thread(bot)
    if not th:
        return
    state = _read_state()

    wl_count = len(set(wl)); bl_count = len(set(bl))
    embed = discord.Embed(
        title="Memory WL/BL",
        description="Ringkasan domain whitelisted & blacklisted.\nThread ini menyimpan **memory** agar tidak hilang saat redeploy.",
        color=0x2ecc71
    )
    embed.add_field(name="Whitelist (domains)", value=f"**{wl_count}**", inline=True)
    embed.add_field(name="Blacklist (domains)", value=f"**{bl_count}**", inline=True)
    embed.set_footer(text="Auto-updated")

    # Upsert embed (pinned)
    embed_id = state.get("embed_message_id")
    msg = None
    if embed_id:
        try:
            msg = await th.fetch_message(embed_id)
            await msg.edit(embed=embed)
        except Exception:
            msg = None
    if msg is None:
        try:
            msg = await th.send(embed=embed)
            await msg.pin()
            state["embed_message_id"] = msg.id
        except Exception:
            pass

    # Replace attachments message
    att_id = state.get("attachments_message_id")
    if att_id:
        try:
            old = await th.fetch_message(att_id)
            await old.delete()
        except Exception:
            pass
    try:
        new_msg = await th.send(content="Mirror daftar saat ini:", files=[_txt_file("whitelist.txt", wl), _txt_file("blacklist.txt", bl)])
        state["attachments_message_id"] = new_msg.id
    except Exception:
        pass
    _write_state(state)
