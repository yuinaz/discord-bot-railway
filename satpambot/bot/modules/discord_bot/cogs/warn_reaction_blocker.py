
from __future__ import annotations
import os
import asyncio
from typing import Set
import discord
from discord.ext import commands

def _parse_blocklist(s: str) -> Set[str]:
    raw = [x.strip() for x in s.split(",") if x.strip()]
    # normalize by stripping variation selector where applicable
    return set(raw)

BLOCKLIST = _parse_blocklist(os.getenv("WARN_REACTION_BLOCKLIST", "⚠️,⚠"))
REMOVE_DELAY_S = float(os.getenv("WARN_REACTION_REMOVE_DELAY_S", "0.0"))
DISABLED = os.getenv("WARN_REACTION_DISABLE", "0") in ("1", "true", "yes")

class WarnReactionBlocker(commands.Cog):
    """Hapus reaction warning (⚠️/⚠) secepat mungkin (default instan)."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if DISABLED:
            return
        emoji_str = str(payload.emoji)
        if emoji_str not in BLOCKLIST:
            return
        await self._remove(payload)

    async def _remove(self, payload: discord.RawReactionActionEvent):
        try:
            channel = self.bot.get_channel(payload.channel_id) or await self.bot.fetch_channel(payload.channel_id)
            if not hasattr(channel, "get_partial_message"):
                return
            msg = await channel.fetch_message(payload.message_id)
            # optional delay (default 0.0s = instant)
            if REMOVE_DELAY_S > 0:
                await asyncio.sleep(REMOVE_DELAY_S)
            # Remove this user's reaction if possible
            await msg.remove_reaction(payload.emoji, payload.member or discord.Object(id=payload.user_id))
        except discord.Forbidden:
            # bot lacks 'Manage Messages' or 'Add Reactions' permissions—silently ignore
            pass
        except Exception:
            pass

async def setup(bot: commands.Bot):
    await bot.add_cog(WarnReactionBlocker(bot))
