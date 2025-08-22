
# Simple in-memory live stats store (optional).
# External modules can import `set_stats` to push live stats to dashboard.
_stats = {
    "guilds": 0, "members": 0, "online": 0, "channels": 0,
    "threads": 0, "latency_ms": 0, "updated": 0
}
def get_stats():
    return dict(_stats)
def set_stats(d):
    _stats.update({k: d.get(k, _stats.get(k)) for k in _stats.keys()})
    return get_stats()


# --- simple phash store ---
_phash = []
def get_phash():
    global _phash
    try:
        return list(_phash)
    except Exception:
        return []
def add_phash(v):
    global _phash
    try:
        _phash.append(str(v))
    except Exception:
        pass
