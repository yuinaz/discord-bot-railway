# log_upsert.py — Thin wrapper to update log/status message via MessageKeeper
from __future__ import annotations
from typing import Optional, Union
import discord
from .message_keeper import get_keeper

async def upsert_status(bot: discord.Client, channel: Union[int, str, discord.abc.Messageable], key: str, text: str):
    """Edit/Upsert a single status line per (channel,key)."""
    keeper = get_keeper(bot)
    await keeper.update(channel, key, content=text)
