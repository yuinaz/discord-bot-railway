# Auto-applied at Python startup if this file is on sys.path (project root).
# - Enables fast-start miner delays & intervals (override via env MINER_FAST_START=0)
# - Provides fallback for PublicChatGate report channel using LOG_CHANNEL_ID/etc.
import os, sys

def _set_if_empty(name: str, value) -> None:
    if os.getenv(name) in (None, ""):
        os.environ[name] = str(value)

# --------- Miner fast start ---------
# Enable by default so testing feels instant. Disable by setting MINER_FAST_START=0.
FAST = os.getenv("MINER_FAST_START", "1")
if FAST == "1":
    _set_if_empty("TEXT_MINER_DELAY_SEC", 5)       # default ~5s
    _set_if_empty("TEXT_MINER_INTERVAL_SEC", 180)  # every 3m
    _set_if_empty("PHISH_MINER_DELAY_SEC", 7)      # default ~7s
    _set_if_empty("PHISH_MINER_INTERVAL_SEC", 300) # every 5m
    _set_if_empty("SLANG_MINER_DELAY_SEC", 9)      # default ~9s
    _set_if_empty("SLANG_MINER_INTERVAL_SEC", 300) # every 5m
    # Optional caps to avoid overload if miner supports limits:
    _set_if_empty("PHISH_MINER_LIMIT", 200)
    _set_if_empty("SLANG_MINER_PER_CHANNEL", 200)
# Print once so user sees it's active even if logging not configured yet
try:
    sys.stderr.write(f"[sitecustomize] MINER_FAST_START={FAST} "
                     f"(TEXT_delay={os.getenv('TEXT_MINER_DELAY_SEC')}, "
                     f"PHISH_delay={os.getenv('PHISH_MINER_DELAY_SEC')}, "
                     f"SLANG_delay={os.getenv('SLANG_MINER_DELAY_SEC')})\n")
except Exception:
    pass

# --------- PublicChatGate fallback ---------
# If PUBLIC_REPORT_CHANNEL_ID isn't set, fallback to other known IDs.
if not os.getenv("PUBLIC_REPORT_CHANNEL_ID"):
    cid = (os.getenv("PUBLIC_CHAT_REPORT_CHANNEL_ID")
           or os.getenv("REPORT_CHANNEL_ID")
           or os.getenv("SATPAMBOT_LOG_CHANNEL_ID")
           or os.getenv("LOG_CHANNEL_ID"))
    if cid:
        os.environ["PUBLIC_REPORT_CHANNEL_ID"] = cid
        try:
            sys.stderr.write(f"[sitecustomize] PUBLIC_REPORT_CHANNEL_ID←{cid} (fallback)\n")
        except Exception:
            pass
