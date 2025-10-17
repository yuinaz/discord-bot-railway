import discord
from discord.ext import commands

class PersonaGetterFallback(commands.Cog):
    """If PersonaOverlay lacks get_active_persona(), provide a safe getter on bot."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        if not hasattr(bot, "get_active_persona"):
            def _fallback(*args, **kwargs):
                # minimal persona
                return {"name":"Leina", "style":"helpful, concise, friendly", "prefix":"Leina"}
            setattr(bot, "get_active_persona", _fallback)

async def setup(bot: commands.Bot):
    await bot.add_cog(PersonaGetterFallback(bot))
