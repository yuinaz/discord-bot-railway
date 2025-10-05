from __future__ import annotations

from discord.ext import commands


async def _load_invite_cog(bot: commands.Bot) -> None:
    try:
        from ..cogs.anti_invite_autoban import AntiInviteAutoban
    except Exception:
        return
    try:
        # If not already loaded, add the cog lazily
        if not any(isinstance(c, AntiInviteAutoban) for c in getattr(getattr(bot, "cogs", None), "values", lambda: {})() or []):
            await bot.add_cog(AntiInviteAutoban(bot))  # type: ignore[attr-defined]
    except Exception:
        pass

try:
    _bot = globals().get("bot")
    if isinstance(_bot, commands.Bot):
        _bot.loop.create_task(_load_invite_cog(_bot))
except Exception:
    pass
