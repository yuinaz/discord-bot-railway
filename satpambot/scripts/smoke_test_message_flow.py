# satpambot/scripts/smoke_test_message_flow.py
import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import asyncio
import types
import discord
from discord.ext import commands

# handler message dari repo mono
from satpambot.bot.modules.discord_bot.message_handlers import handle_on_message  # type: ignore

def make_test_bot():
    intents = discord.Intents.none()
    intents.guilds = True
    intents.messages = True
    intents.message_content = True
    return commands.Bot(command_prefix="!", intents=intents)

class DummyChannel:
    def __init__(self):
        self.sent = []
    async def send(self, *a, **kw):
        self.sent.append((a, kw))
        return types.SimpleNamespace(id=1)

class DummyAuthor:
    def __init__(self, is_bot=False):
        self.bot = is_bot
        self.id = 1234
        self.name = "tester"

class DummyMessage:
    def __init__(self, content, is_bot=False):
        self.content = content
        self.author = DummyAuthor(is_bot)
        self.channel = DummyChannel()
        self.guild = types.SimpleNamespace(id=1, name="TestGuild")
        self.attachments = []
        self.embeds = []
        self.id = 999

async def main():
    bot = make_test_bot()
    # pesan biasa
    msg = DummyMessage("hello world", is_bot=False)
    await handle_on_message(msg)  # harus tidak error
    print("OK: handle_on_message executed (normal message)")
    # pesan dari bot (should be ignored)
    botmsg = DummyMessage("from bot", is_bot=True)
    await handle_on_message(botmsg)
    print("OK: handle_on_message ignored bot message")

if __name__ == "__main__":
    asyncio.run(main())
