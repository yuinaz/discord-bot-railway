
from __future__ import annotations
from typing import Dict, Tuple
import threading
from satpambot.bot.modules.discord_bot.utils.atomic_json import AtomicJsonStore
class XPStore:
    def __init__(self, path: str):
        self.store = AtomicJsonStore(path)
        self.lock = threading.Lock()
        self.store.load()
        if not isinstance(self.store.get(), dict): self.store._data = {}
    def _calc_level(self, xp: int) -> str:
        if xp >= 1000: return 'S'
        if xp >= 500:  return 'A'
        if xp >= 250:  return 'B'
        if xp >= 100:  return 'C'
        return 'TK'
    def add_xp(self, guild_id: int, user_id: int, add: int) -> Tuple[int, str]:
        with self.lock:
            g = self.store.get().setdefault(str(guild_id), {})
            u = g.setdefault(str(user_id), {'xp': 0, 'level': 'TK'})
            u['xp'] = int(u.get('xp', 0)) + int(add)
            u['level'] = self._calc_level(u['xp'])
            self.store.write_atomic()
            return u['xp'], u['level']
    def get_user(self, guild_id: int, user_id: int) -> Dict:
        return self.store.get().get(str(guild_id), {}).get(str(user_id), {'xp': 0, 'level': 'TK'})
