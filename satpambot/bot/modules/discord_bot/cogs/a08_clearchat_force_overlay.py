import asyncio
from datetime import datetime, timezone, timedelta
from typing import Iterable, List

import discord
from discord import app_commands
from discord.ext import commands

ALLOW_IDS_FALLBACK = [1400375184048787566]

def _get_allow_ids(bot: commands.Bot) -> List[int]:
    try:
        from satpambot.config.runtime import cfg
        ids = cfg("CLEARCHAT_FORCE_CHANNELS")
        if isinstance(ids, str):
            ids = [int(x.strip()) for x in ids.split(",") if x.strip().isdigit()]
        if hasattr(ids, "__iter__"):
            ids = list(map(int, ids))
            if ids:
                return ids
        log_id = cfg("LOG_CHANNEL_ID")
        if log_id:
            return [int(log_id)]
    except Exception:
        pass
    return ALLOW_IDS_FALLBACK[:]

class ClearChatForce(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def _bulk_delete_ids(self, channel_id: int, ids: List[int]) -> int:
        deleted = 0
        while ids:
            chunk = ids[:100]
            del ids[:100]
            if len(chunk) == 1:
                try:
                    await self.bot.http.delete_message(channel_id, chunk[0])
                    deleted += 1
                except Exception:
                    pass
                continue
            try:
                await self.bot.http.bulk_delete_messages(channel_id, chunk)
                deleted += len(chunk)
            except Exception:
                for mid in chunk:
                    try:
                        await self.bot.http.delete_message(channel_id, mid)
                        deleted += 1
                    except Exception:
                        pass
            await asyncio.sleep(0.2)
        return deleted

    async def _purge_force_all(self, channel: discord.TextChannel) -> int:
        now = datetime.now(timezone.utc)
        younger, older = [], []
        async for msg in channel.history(limit=None, oldest_first=False):
            age = now - msg.created_at
            (younger if age < timedelta(days=14) else older).append(msg.id)
            if len(younger) >= 500:
                await self._bulk_delete_ids(channel.id, younger); younger.clear()
        deleted = 0
        if younger:
            deleted += await self._bulk_delete_ids(channel.id, younger)
        for mid in older:
            try:
                await self.bot.http.delete_message(channel.id, mid)
                deleted += 1
            except Exception:
                pass
            if deleted % 25 == 0:
                await asyncio.sleep(0.25)
        return deleted

    @app_commands.command(name="clearchat", description="Force clear THIS channel immediately (no prompts).")
    @app_commands.default_permissions(manage_messages=True)
    @app_commands.guild_only()
    async def clearchat(self, interaction: discord.Interaction):
        ch = interaction.channel
        if not isinstance(ch, discord.TextChannel):
            await interaction.response.send_message("Not a text channel.", ephemeral=True); return
        allow_ids = _get_allow_ids(self.bot)
        if allow_ids and ch.id not in allow_ids:
            await interaction.response.send_message("This command is restricted to the log channel.", ephemeral=True); return
        await interaction.response.defer(ephemeral=True, thinking=False)
        deleted = await self._purge_force_all(ch)
        await interaction.followup.send(f"OK — deleted {deleted} messages.", ephemeral=True)

async def setup(bot: commands.Bot):
    try:
        existing = bot.tree.get_command("clearchat")
        if existing:
            bot.tree.remove_command(existing.name, type=existing.type)
    except Exception:
        pass
    await bot.add_cog(ClearChatForce(bot))
