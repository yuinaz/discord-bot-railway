# -*- coding: utf-8 -*-
"""
Patched ChatNeuroLite for OpenAI SDK v1.
- Uses helpers.openai_client instead of deprecated openai.ChatCompletion
- Robust history normalization (fixes ValueError unpack bug)
- Reads API key from env (OPENAI_API_KEY or OPENAI-KEY)
"""
from __future__ import annotations
import asyncio
from typing import List, Dict, Any
import logging

import discord
from discord.ext import commands

from ..helpers.openai_client import chat_once
def normalize_history(past):
    """
    Accepts list of tuples of either (role, content) or (id, role, content).
    Returns list[dict]: [{"role": .., "content": ..}, ...]
    """
    result = []
    if not past:
        return result
    for item in past:
        # (role, content)
        if isinstance(item, (list, tuple)) and len(item) == 2:
            role, content = item
        # (id, role, content)
        elif isinstance(item, (list, tuple)) and len(item) == 3:
            _, role, content = item
        else:
            # Fallback: stringify
            role, content = "user", str(item)
        result.append({"role": str(role), "content": str(content)})
    return result


log = logging.getLogger(__name__)

SYSTEM_PROMPT = "Kamu Neuro-Lite, tsundere JP-ID. Jawab singkat, ramah, tidak vulgar."

class ChatNeuroLite(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        try:
            if message.author.bot:
                return
            # Only reply when bot is mentioned or in a designated channel (simple heuristic)
            if not (message.mentions and self.bot.user in message.mentions):
                return

            user_text = message.clean_content.replace(f"@{self.bot.user.name}", "").strip()
            if not user_text:
                return

            # Past can be provided by other cogs; be defensive
            past = getattr(message, "nl_past", [])
            msgs: List[Dict[str, str]] = [{{"role": "system", "content": SYSTEM_PROMPT}}]
            msgs += normalize_history(past)
            msgs.append({{"role": "user", "content": user_text}})

            # Call OpenAI v1
            reply = chat_once(msgs, temperature=0.6)
            if not reply:
                reply = "えっと…今ちょっと調子悪いかも。後で試してみて？"

            await message.channel.send(reply[:1800])
        except Exception:
            log.exception("[chat_neurolite] error in on_message")
            # Fail softly—don't crash gateway
            try:
                await message.add_reaction("❌")
            except Exception:
                pass

async def setup(bot: commands.Bot):
    await bot.add_cog(ChatNeuroLite(bot))
