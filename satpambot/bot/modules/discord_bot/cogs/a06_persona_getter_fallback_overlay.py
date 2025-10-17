from discord.ext import commands

class PersonaGetterFallbackOverlay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        cog = bot.get_cog("PersonaOverlay")
        if cog and not hasattr(cog, "get_active_persona"):
            async def _get_active_persona(guild):
                return "default"
            setattr(cog, "get_active_persona", _get_active_persona)

    @commands.Cog.listener()
    async def on_ready(self):
        pass

async def setup(bot):
    await bot.add_cog(PersonaGetterFallbackOverlay(bot))
