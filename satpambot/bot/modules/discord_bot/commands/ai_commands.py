import discord
from discord.ext import commands
from modules.discord_bot.ai.chatgpt_handler import call_chatgpt

def setup_ai_commands(bot):
    @bot.command(name="ask", help="Tanyakan sesuatu ke AI (ChatGPT)")
    async def ask(ctx, *, question: str):
        await ctx.trigger_typing()
        response = await call_chatgpt(question)
        await ctx.reply(response, mention_author=False)
