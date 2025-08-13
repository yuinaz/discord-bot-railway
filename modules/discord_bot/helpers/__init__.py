# modules/discord_bot/helpers/__init__.py
# Back-compat shim: re-export commonly imported names from helpers.env
# so imports like `from modules.discord_bot.helpers import LOG_CHANNEL_ID` keep working.

from . import env as _env  # type: ignore

BOT_TOKEN           = getattr(_env, "BOT_TOKEN", "")
BOT_PREFIX          = getattr(_env, "BOT_PREFIX", "!")
BOT_INTENTS         = getattr(_env, "BOT_INTENTS", None)
FLASK_ENV           = getattr(_env, "FLASK_ENV", "production")

LOG_CHANNEL_ID      = getattr(_env, "LOG_CHANNEL_ID", 0)
LOG_CHANNEL_NAME    = getattr(_env, "LOG_CHANNEL_NAME", "log-botphising")

# Optional helpers (will be None if not present)
resolve_log_channel      = getattr(_env, "resolve_log_channel", None)
resolve_ban_log_channel  = getattr(_env, "resolve_ban_log_channel", None)
env_log_summary          = getattr(_env, "env_log_summary", lambda: "")
