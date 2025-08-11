# --- injected override: force log channel by ID ---
try:
    from ..helpers import log_utils as _lu
    _lu.LOG_CHANNEL_ID = int("1400375184048787566")
except Exception:
    pass
