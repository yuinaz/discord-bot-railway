from __future__ import annotations
import os, logging
import discord
from discord.ext import commands

log = logging.getLogger(__name__)
REQUIRE_MESSAGE_CONTENT = os.getenv("INTENTS_PROBE_REQUIRE_MESSAGE_CONTENT", "1") not in ("0","false","False")

def _summarize(intents: discord.Intents) -> str:
    keys = ("guilds","members","message_content","emojis","reactions","messages","presences","guild_messages","dm_messages")
    return ", ".join([f"{k}={getattr(intents,k)}" for k in keys if hasattr(intents,k)])

class IntentsProbe(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._check()

    def _check(self):
        intents = getattr(self.bot, "intents", None)
        if not isinstance(intents, discord.Intents):
            log.error("[intents-probe] bot.intents tidak tersedia / bukan discord.Intents. "
                      "Gunakan discord.Intents.default() lalu set message_content=True.")
            return
        if not intents.guilds:
            log.warning("[intents-probe] intents.guilds=False — sebaiknya True. "
                        "Ganti Intents.none() -> Intents.default() saat membuat bot.")
        if REQUIRE_MESSAGE_CONTENT and not intents.message_content:
            log.warning("[intents-probe] message_content=False — aktifkan di kode (intents.message_content=True) "
                        "dan di Discord Dev Portal (Privileged Intent).")
        log.info("[intents-probe] summary: %s", _summarize(intents))

async def setup(bot: commands.Bot):
    await bot.add_cog(IntentsProbe(bot))
