
# -*- coding: utf-8 -*-
"""ChatNeuroLite Silent Guard
- Blocks any public-channel replies from ChatNeuroLite (DM-only).
- Optionally disables name-wake auto-reply cogs.
- Zero config required; can be controlled via env vars below.

ENV (all optional):
  DISABLE_NAME_WAKE=1   # default 1 (disable name-wake cogs)
  SILENT_PUBLIC=1       # default 1 (never reply in guild/public channels)
  PUBLIC_MIN_PROGRESS=101  # float 0..100; >100 means never allow public replies
  ALLOW_DM=1            # default 1 (allow replies in DM)
"""
from __future__ import annotations

import os
import importlib
from typing import Any
from discord.ext import commands

_ENV_DISABLE_NAME_WAKE = os.getenv("DISABLE_NAME_WAKE", "1")
_ENV_SILENT_PUBLIC = os.getenv("SILENT_PUBLIC", "1")
_ENV_PUBLIC_MIN_PROGRESS = float(os.getenv("PUBLIC_MIN_PROGRESS", "101"))
_ENV_ALLOW_DM = os.getenv("ALLOW_DM", "1")

def _patch_neurolite() -> None:
    """Monkey-patch ChatNeuroLite.on_message to enforce DM-only (by default)."""
    try:
        cn = importlib.import_module("satpambot.bot.modules.discord_bot.cogs.chat_neurolite")
    except Exception:
        return
    ChatNeuroLite = getattr(cn, "ChatNeuroLite", None)
    if ChatNeuroLite is None:
        return
    if getattr(ChatNeuroLite, "_silent_guard_patched", False):
        return

    original = ChatNeuroLite.on_message

    async def on_message_patched(self, message: Any):
        # ignore other bots
        if getattr(getattr(message, "author", None), "bot", False):
            return

        guild = getattr(message, "guild", None)
        is_dm = guild is None

        # 1) Public/guild messages: block when SILENT_PUBLIC=1 (default)
        if guild is not None:
            if _ENV_SILENT_PUBLIC == "1":
                return
            # Optional: gating by learning progress env (if ever used later)
            try:
                progress = float(getattr(self, "learning_progress", 0.0))
            except Exception:
                progress = 0.0
            if progress < _ENV_PUBLIC_MIN_PROGRESS:
                return

            # You could add mention checks here in the future if needed.
            return  # still block by default for safety

        # 2) DM handling:
        if is_dm and _ENV_ALLOW_DM == "1":
            return await original(self, message)
        else:
            return

    ChatNeuroLite.on_message = on_message_patched  # type: ignore[attr-defined]
    ChatNeuroLite._silent_guard_patched = True

class ChatNeuroLiteGuard(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        _patch_neurolite()

    @commands.Cog.listener()
    async def on_ready(self):
        # Optionally disable name-wake auto-repliers
        if _ENV_DISABLE_NAME_WAKE == "1":
            to_disable = []
            for ext in list(self.bot.extensions.keys()):
                if ext.endswith("name_wake_autoreply") or ext.endswith("name_wake_autoreply_enhanced"):
                    to_disable.append(ext)
            for ext in to_disable:
                try:
                    await self.bot.unload_extension(ext)
                except Exception:
                    pass

async def setup(bot: commands.Bot):
    await bot.add_cog(ChatNeuroLiteGuard(bot))

# Back-compat for sync loaders
def setup(bot: commands.Bot):
    # discord.py v2 prefers async setup, but we keep sync for robustness
    bot.add_cog(ChatNeuroLiteGuard(bot))
