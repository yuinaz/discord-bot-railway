from __future__ import annotations

import logging
import os
from typing import Set

import discord
from discord.ext import commands

from satpambot.ml import shadow_metrics as sm

log = logging.getLogger(__name__)


def _parse_skip_channels() -> Set[int]:
    raw = os.getenv("SKIP_CHANNELS") or os.getenv("SKIP_CHANNEL_IDS") or ""
    ids: Set[int] = set()
    if not raw:
        return ids
    # remove spaces, split by comma
    for tok in raw.replace(" ", "").split(","):
        if not tok:
            continue
        try:
            ids.add(int(tok))
        except ValueError:
            log.warning("[shadow_learn_observer] Skip channel id invalid: %r", tok)
    return ids


class ShadowLearnObserver(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.skip_ids: Set[int] = _parse_skip_channels()
        if self.skip_ids:
            log.info(
                "[shadow_learn_observer] skip channels active: %s",
                ",".join(str(x) for x in sorted(self.skip_ids)),
            )
        else:
            log.info("[shadow_learn_observer] no skip channels configured")

    @commands.Cog.listener()
    async def on_message(self, m: discord.Message):
        # Ignore DMs and bots
        if m.guild is None or m.author.bot:
            return

        # Skip configured channel IDs
        if m.channel and m.channel.id in self.skip_ids:
            return

        # Only bump metrics; never hard-fail the cog
        try:
            sm.bump("exposures_total", 1.0, user_id=m.author.id)
        except Exception as e:
            log.warning("[shadow_learn_observer] metrics write failed: %r", e)


async def setup(bot: commands.Bot):
    # discord.py v2 requires async setup()
    await bot.add_cog(ShadowLearnObserver(bot))