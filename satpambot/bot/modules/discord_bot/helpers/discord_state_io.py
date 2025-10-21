import logging
log = logging.getLogger(__name__)

def apply_state(obj):
    """Apply state dict safely. Accepts None (no-op)."""
    if not obj:
        log.info("[state_io] empty/None state, skip apply")
        return
    # Original structure assumed obj is dict with possible keys:
    # sticker_stats -> list of (emo, sent, succ)
    try:
        for emo, sent, succ in obj.get("sticker_stats", []):
            # do your sticker application here (kept as a placeholder)
            pass
    except Exception as e:
        log.debug("[state_io] apply sticker_stats skipped: %s", e)
    # Add more guarded applications here as needed.
