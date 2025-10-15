import os, re, sys, json

def warn(msg):
    print("WARN:", msg)
def info(msg):
    print("INFO:", msg)

ok = True
token = os.getenv("DISCORD_TOKEN") or os.getenv("BOT_TOKEN")
if token:
    info("Token: PRESENT (hidden)")
else:
    warn("Token: MISSING — set DISCORD_TOKEN in SatpamBot.env or secrets/SatpamBot.env")
    ok = False

log_id = os.getenv("LOG_CHANNEL_ID", "").strip()
log_name = os.getenv("LOG_CHANNEL_NAME", "").strip() or "log-botphising"
if log_id and not re.fullmatch(r"\d{15,25}", log_id):
    warn(f"LOG_CHANNEL_ID looks non-numeric: {log_id!r}")
    ok = False
elif log_id:
    info(f"LOG_CHANNEL_ID: {log_id}")
else:
    info(f"LOG_CHANNEL_ID not set; will use LOG_CHANNEL_NAME='{log_name}' fallback")

# check quiet + thread flags
for k in ["DM_MUZZLE","SELFHEAL_ENABLE","AUTOMATON_ENABLE","SELFHEAL_QUIET","AUTOMATON_QUIET","SELFHEAL_THREAD_DISABLE","AUTOMATON_THREAD_DISABLE"]:
    v = os.getenv(k)
    info(f"{k}={v!r}")

# live config wiring
src = os.getenv("LIVE_CONFIG_SOURCE","")
path = os.getenv("LIVE_CONFIG_PATH","")
info(f"LIVE_CONFIG_SOURCE={src!r} LIVE_CONFIG_PATH={path!r}")

# print summary and exit code
print("SUMMARY:", json.dumps({
    "token": bool(token),
    "log_id": log_id,
    "log_name": log_name,
    "live_cfg_source": src,
    "live_cfg_path": path,
}, ensure_ascii=False))

sys.exit(0 if ok else 1)
