import openai, os
from discord.ext import commands
from modules.discord_bot import bot

openai.api_key = os.getenv("OPENAI_API_KEY")

@bot.command(name="gpt")
@commands.has_permissions(administrator=True)
async def gpt_command(ctx, *, prompt: str):
    await ctx.trigger_typing()
    try:
        res = openai.ChatCompletion.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4"),
            messages=[{"role": "user", "content": prompt}]
        )
        reply = res['choices'][0]['message']['content']
        await ctx.reply(reply[:1900])
    except Exception as e:
        await ctx.send(f"❌ Gagal menjawab: {e}")