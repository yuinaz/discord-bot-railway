
# PATCHED: emit lock with safe TTL lookup (interval_sec may not exist)
import time
try:
    from satpambot.bot.modules.discord_bot.cogs.patch_helpers_qna_guard import _claim_qna_slot
except Exception:
    _claim_qna_slot = None

def _ttl_from_self(self):
    for k in ("interval_sec", "interval", "interval_min"):
        v = getattr(self, k, None)
        try:
            if v is None: 
                continue
            return int(v)
        except Exception:
            continue
    return 180  # fallback

# --- begin: NX/EX emit guard ---
if _claim_qna_slot:
    _ttl = max(60, _ttl_from_self(self))
    if not _claim_qna_slot(_ttl):
        # another poster already emitted within the TTL window; skip sending
        return
# --- end: NX/EX emit guard ---
