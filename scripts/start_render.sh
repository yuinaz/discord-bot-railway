#!/usr/bin/env bash
set -Eeuo pipefail

# Move to repo root (script is in ./scripts)
cd "$(dirname "$0")/.."

export PYTHONUNBUFFERED=1
export PYTHONDONTWRITEBYTECODE=1

echo "[start_render] Python: $(python -V 2>&1)"

# Load env from repo files (secrets override)
if [[ -f secrets/SatpamBot.env ]]; then
  echo "[start_render] Loading secrets/SatpamBot.env"
  set -a; source secrets/SatpamBot.env; set +a
elif [[ -f SatpamBot.env ]]; then
  echo "[start_render] Loading SatpamBot.env"
  set -a; source SatpamBot.env; set +a
else
  echo "[start_render] No SatpamBot.env found (will rely on Render env or service vars)"
fi

# Live-config defaults so we don't depend on Render dashboard toggles
export LIVE_CONFIG_SOURCE="${LIVE_CONFIG_SOURCE:-file}"
export LIVE_CONFIG_PATH="${LIVE_CONFIG_PATH:-./config/live_config.json}"
export LIVE_CONFIG_POLL_INTERVAL="${LIVE_CONFIG_POLL_INTERVAL:-4.0}"

# Quiet + auto-thread sane defaults
export DM_MUZZLE="${DM_MUZZLE:-log}"
export SELFHEAL_ENABLE="${SELFHEAL_ENABLE:-1}"
export AUTOMATON_ENABLE="${AUTOMATON_ENABLE:-1}"
export SELFHEAL_QUIET="${SELFHEAL_QUIET:-1}"
export AUTOMATON_QUIET="${AUTOMATON_QUIET:-1}"
export SELFHEAL_THREAD_DISABLE="${SELFHEAL_THREAD_DISABLE:-0}"
export AUTOMATON_THREAD_DISABLE="${AUTOMATON_THREAD_DISABLE:-0}"

# Logging channel config (ID wins, name is fallback)
export LOG_CHANNEL_NAME="${LOG_CHANNEL_NAME:-log-botphising}"

# Print safe summary (no secrets)
python - <<'PY'
import os, json
safe_keys = [
  "LIVE_CONFIG_SOURCE","LIVE_CONFIG_PATH","LIVE_CONFIG_POLL_INTERVAL",
  "DM_MUZZLE","SELFHEAL_ENABLE","AUTOMATON_ENABLE","SELFHEAL_QUIET","AUTOMATON_QUIET",
  "SELFHEAL_THREAD_DISABLE","AUTOMATON_THREAD_DISABLE","LOG_CHANNEL_ID","LOG_CHANNEL_NAME",
]
safe = {k: os.environ.get(k,"") for k in safe_keys if k in os.environ}
print("[start_render] ENV summary:", json.dumps(safe, ensure_ascii=False))
token_set = bool(os.environ.get("DISCORD_TOKEN") or os.environ.get("BOT_TOKEN"))
print("[start_render] Token present:", "YES" if token_set else "NO")
PY

# Optional preflight check (won't block boot)
python scripts/verify_render_setup.py || true

# Boot the bot
exec python -m satpambot.bot.modules.discord_bot.shim_runner
