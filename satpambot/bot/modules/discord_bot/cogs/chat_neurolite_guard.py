# -*- coding: utf-8 -*-
"""ChatNeuroLite Silent Guard (safe TKSD variant)
- Blocks public-channel bot messages (optional).
- Optionally unloads name-wake cogs.
- Async setup; no double-await; compatible with discord.py v2.
Env (optional):
  DISABLE_NAME_WAKE=1    default 1
  SILENT_PUBLIC=1        default 1
  ALLOW_DM=1             default 1 (unused in this guard, reserved)
"""
from __future__ import annotations

import logging
import os
import discord
from discord.ext import commands

log = logging.getLogger(__name__)


class ChatNeuroLiteGuard(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.disable_name_wake = (os.getenv("DISABLE_NAME_WAKE", "1") != "0")
        self.silent_public = (os.getenv("SILENT_PUBLIC", "1") != "0")
        self.allow_dm = (os.getenv("ALLOW_DM", "1") != "0")

    async def cog_load(self):
        # Optionally unload name-wake cogs to hard-disable public auto-replies.
        if self.disable_name_wake:
            to_unload = [
                "satpambot.bot.modules.discord_bot.cogs.name_wake_autoreply",
                "satpambot.bot.modules.discord_bot.cogs.name_wake_autoreply_enhanced",
            ]
            for ext in to_unload:
                try:
                    await self.bot.unload_extension(ext)
                    log.info("[chat_neurolite_guard] unloaded %s", ext)
                except Exception:
                    pass

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # If configured silent_public, nuke bot's own public messages.
        if self.silent_public and message.guild and message.author and self.bot.user and message.author.id == self.bot.user.id:
            try:
                await message.delete()
                log.info("[chat_neurolite_guard] deleted bot public reply in %s", message.channel)
            except Exception:
                pass


async def setup(bot: commands.Bot):
    await bot.add_cog(ChatNeuroLiteGuard(bot))
