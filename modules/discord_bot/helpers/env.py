# modules/discord_bot/helpers/env.py
from __future__ import annotations
import os
import discord

def _truthy(x: str | None) -> bool:
    return str(x or "").strip().lower() in ("1", "true", "yes", "on")

# --- PROFILE DETECTOR ---
# Urutan:
# 1) ENV_PROFILE (jika ada) → pakai itu (mis. "local", "render", "production")
# 2) Terdeteksi Render (RENDER / RENDER_SERVICE_ID / RENDER_EXTERNAL_URL) → "render"
# 3) Default ke "local" (lebih enak buat dev di mesin sendiri)
_PROFILE = os.getenv("ENV_PROFILE")
if not _PROFILE:
    if any(os.getenv(k) for k in ("RENDER", "RENDER_SERVICE_ID", "RENDER_EXTERNAL_URL")):
        _PROFILE = "render"
    else:
        _PROFILE = "local"

# simpan untuk diagnosa
os.environ["ENV_PROFILE_ACTIVE"] = _PROFILE

# --- PREFIX ---
BOT_PREFIX = os.getenv("BOT_PREFIX", "!")

# --- INTENTS ---
def _build_intents() -> discord.Intents:
    intents = discord.Intents.default()
    intents.guilds = True
    intents.members = True
    intents.messages = True
    intents.bans = True
    intents.invites = True
    intents.message_content = True  # penting untuk prefix "!"
    return intents

BOT_INTENTS = _build_intents()

# --- MODE/LOGGING LABEL ---
FLASK_ENV = "development" if _PROFILE in ("local", "dev") else "production"

# --- OAUTH (opsional) ---
OAUTH2_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID") or os.getenv("OAUTH2_CLIENT_ID")
OAUTH2_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET") or os.getenv("OAUTH2_CLIENT_SECRET")

# --- TOKEN RESOLVER ---
# - LOCAL/DEV  : pakai DISCORD_BOT_TOKEN_LOCAL dulu, fallback ke DISCORD_BOT_TOKEN/BOT_TOKEN
# - RENDER/PROD: pakai DISCORD_BOT_TOKEN atau BOT_TOKEN
def get_bot_token() -> str | None:
    if _PROFILE in ("local", "dev"):
        return (
            os.getenv("DISCORD_BOT_TOKEN_LOCAL")
            or os.getenv("DISCORD_BOT_TOKEN")
            or os.getenv("BOT_TOKEN")
        )
    # render/production
    return os.getenv("DISCORD_BOT_TOKEN") or os.getenv("BOT_TOKEN")

def get_profile() -> str:
    return _PROFILE
