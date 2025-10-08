from __future__ import annotations
import logging
import discord
from discord.ext import commands

log = logging.getLogger(__name__)

class SelfhealProposalFilter(commands.Cog):
    """Global filter: blokir DM 'Proposal: …' dan tiket auto-enable cog."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    async def cog_load(self):
        try:
            # Monkeypatch send_selfheal di router
            from .selfheal_router import send_selfheal as _orig
            import satpambot.bot.modules.discord_bot.cogs.selfheal_router as router

            async def _filtered(bot, embed: discord.Embed, *a, **k):
                try:
                    if isinstance(embed, discord.Embed):
                        t = (embed.title or "").lower()
                        d = (embed.description or "").lower()
                        txt = f"{t}\n{d}"
                        # drop embed yang mengandung indikasi Proposal
                        if "proposal:" in txt or "enable_cog" in txt or "ticket" in txt:
                            log.info("[selfheal-filter] drop proposal DM: %s", (embed.title or ""))
                            return
                except Exception:
                    pass
                return await _orig(bot, embed, *a, **k)

            router.send_selfheal = _filtered  # patch global
            log.info("[selfheal-filter] send_selfheal wrapped")
        except Exception as e:
            log.warning("[selfheal-filter] wrap failed: %s", e)

    async def cog_unload(self):
        # Best-effort: biarkan wrapper tetap; tidak fatal
        pass

async def setup(bot: commands.Bot):
    await bot.add_cog(SelfhealProposalFilter(bot))
