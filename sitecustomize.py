# Auto-applied at Python startup if this file is on sys.path (project root).
# Balanced miner profile: avoid rate limits with moderate cadence.
# You can override by setting the same envs before starting Python.
import os, sys

def _force_if_absent(name: str, value) -> None:
    # Only set if not explicitly provided by user
    if os.getenv(name) in (None, ""):
        os.environ[name] = str(value)

PROFILE = os.getenv("MINER_PROFILE", "balanced")  # profiles: balanced|custom
if PROFILE == "balanced":
    # Start delays (staggered) to avoid burst
    _force_if_absent("TEXT_MINER_DELAY_SEC", 30)   # first snapshot after 30s
    _force_if_absent("PHISH_MINER_DELAY_SEC", 35)
    _force_if_absent("SLANG_MINER_DELAY_SEC", 40)
    # Intervals (5 minutes)
    _force_if_absent("TEXT_MINER_INTERVAL_SEC", 300)
    _force_if_absent("PHISH_MINER_INTERVAL_SEC", 300)
    _force_if_absent("SLANG_MINER_INTERVAL_SEC", 300)
    # Sensible caps
    _force_if_absent("PHISH_MINER_LIMIT", 200)
    _force_if_absent("SLANG_MINER_PER_CHANNEL", 100)
    # Optional total budgets if miner supports it
    _force_if_absent("TEXT_MINER_TOTAL_BUDGET", 900)

try:
    sys.stderr.write("[sitecustomize] MINER_PROFILE=%s "
                     "(TEXT_delay=%s/T=%s, PHISH_delay=%s/T=%s, SLANG_delay=%s/T=%s)\n" % (
        PROFILE,
        os.getenv('TEXT_MINER_DELAY_SEC'), os.getenv('TEXT_MINER_INTERVAL_SEC'),
        os.getenv('PHISH_MINER_DELAY_SEC'), os.getenv('PHISH_MINER_INTERVAL_SEC'),
        os.getenv('SLANG_MINER_DELAY_SEC'), os.getenv('SLANG_MINER_INTERVAL_SEC'),
    ))
except Exception:
    pass

# Keep previous fallback for report channel through env if already set elsewhere.
if not os.getenv("PUBLIC_REPORT_CHANNEL_ID"):
    cid = (os.getenv("PUBLIC_CHAT_REPORT_CHANNEL_ID")
           or os.getenv("REPORT_CHANNEL_ID")
           or os.getenv("SATPAMBOT_LOG_CHANNEL_ID")
           or os.getenv("LOG_CHANNEL_ID"))
    if cid:
        os.environ["PUBLIC_REPORT_CHANNEL_ID"] = cid
        try:
            sys.stderr.write(f"[sitecustomize] PUBLIC_REPORT_CHANNEL_ID←{cid} (fallback via env)\n")
        except Exception:
            pass
