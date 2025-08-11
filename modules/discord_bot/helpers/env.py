import os
import discord

def _bool(x: str) -> bool:
    return str(x).strip().lower() in ("1","true","yes","on")

BOT_PREFIX = os.getenv("BOT_PREFIX", "!")
FLASK_ENV = os.getenv("FLASK_ENV", "production")

def build_intents() -> discord.Intents:
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True
    intents.guilds = True
    return intents

BOT_INTENTS = build_intents()

OAUTH2_CLIENT_ID = os.getenv("OAUTH2_CLIENT_ID", "")
OAUTH2_CLIENT_SECRET = os.getenv("OAUTH2_CLIENT_SECRET", "")
