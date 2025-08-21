from threading import RLock
from time import time

_STATS = {"guilds":0,"members":0,"online":0,"channels":0,"threads":0,"latency_ms":0,"updated":0}
_LOCK = RLock()

def set_stats(d: dict):
    with _LOCK:
        _STATS.update(d)
        _STATS["updated"] = int(time())

def get_stats() -> dict:
    with _LOCK:
        return dict(_STATS)
