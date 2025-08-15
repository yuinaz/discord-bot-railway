# satpambot/scripts/smoke_test_commands.py
import os, sys

# pastikan bisa di-run sebagai file
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import asyncio
import discord
from discord.ext import commands

# cogs loader dari repo mono
from satpambot.bot.modules.discord_bot.cogs_loader import load_all_cogs  # type: ignore

def make_test_bot():
    intents = discord.Intents.none()
    intents.guilds = True
    intents.messages = True
    intents.message_content = True
    return commands.Bot(command_prefix="!", intents=intents)

async def main():
    bot = make_test_bot()
    load_all_cogs(bot)  # hanya registrasi, tidak login
    print(f"OK: loaded {len(bot.cogs)} cogs, {sum(len(c.commands) for c in bot.cogs.values())} commands")
    # pastikan beberapa cogs penting ada
    must = {"admin", "info", "slash_sync", "moderation_extras"}
    present = set(n.lower() for n in bot.cogs.keys())
    missing = must - present
    if missing:
        print(f"WARN: missing cogs: {sorted(missing)}")
    else:
        print("OK: essential cogs present")

if __name__ == "__main__":
    asyncio.run(main())
