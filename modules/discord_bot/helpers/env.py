import os
import discord

def _bool(x: str) -> bool:
    return str(x).strip().lower() in ("1","true","yes","on")

# Mode (opsional)
APP_MODE = os.getenv("APP_MODE", "prod").lower()

# --- Token resolution: DISCORD_TOKEN (prod) -> BOT_TOKEN -> DISCORD_BOT_TOKEN_LOCAL (local)
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
BOT_TOKEN = os.getenv("BOT_TOKEN") or DISCORD_TOKEN or os.getenv("DISCORD_BOT_TOKEN_LOCAL")
if not BOT_TOKEN:
    BOT_TOKEN = None  # biar errornya jelas saat start kalau lupa set token

# Prefix & Intents
BOT_PREFIX = os.getenv("BOT_PREFIX", "!")
FLASK_ENV = os.getenv("FLASK_ENV", "production")

def build_intents() -> discord.Intents:
    intents = discord.Intents.default()
    intents.message_content = True
    intents.members = True
    intents.guilds = True
    return intents

BOT_INTENTS = build_intents()

# OAuth (opsional)
OAUTH2_CLIENT_ID = os.getenv("CLIENT_ID", os.getenv("OAUTH2_CLIENT_ID", ""))
OAUTH2_CLIENT_SECRET = os.getenv("CLIENT_SECRET", os.getenv("OAUTH2_CLIENT_SECRET", ""))

# Toggles dari .env
NSFW_INVITE_AUTOBAN   = _bool(os.getenv("NSFW_INVITE_AUTOBAN", "true"))
URL_AUTOBAN_CRITICAL  = _bool(os.getenv("URL_AUTOBAN_CRITICAL", "true"))
URL_RESOLVE_ENABLED   = _bool(os.getenv("URL_RESOLVE_ENABLED", "true"))

# OCR
OCR_SCAM_STRICT = _bool(os.getenv("OCR_SCAM_STRICT", "true"))
OCR_LANG        = os.getenv("OCR_LANG", "eng+ind")

# Channel log status: pakai LOG_CHANNEL_ID, fallback BAN_LOG_CHANNEL_ID
def _to_int(x: str | None, default: int = 0) -> int:
    try:
        return int(str(x).strip())
    except Exception:
        return default

LOG_CHANNEL_ID   = _to_int(os.getenv("LOG_CHANNEL_ID", "") or os.getenv("BAN_LOG_CHANNEL_ID", "1400375184048787566"))
LOG_CHANNEL_NAME = os.getenv("LOG_CHANNEL_NAME", "log-botphising")

# Slash commands: daftar guild untuk sync cepat (comma-separated)
def _to_ints_csv(x: str | None):
    arr = []
    for part in (x or "").split(","):
        part = part.strip()
        if part.isdigit():
            arr.append(int(part))
    return arr

GUILD_IDS = _to_ints_csv(os.getenv("GUILD_ID", os.getenv("GUILD_IDS", "")))  # contoh: "123,456"
