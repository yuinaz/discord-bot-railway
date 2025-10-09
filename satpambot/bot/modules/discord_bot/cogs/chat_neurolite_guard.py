# Async setup; fixes previous 'await await' SyntaxError and non-awaited add_cog warnings.
from discord.ext import commands

class ChatNeuroLiteGuard(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

async def setup(bot: commands.Bot):
    await bot.add_cog(ChatNeuroLiteGuard(bot))
