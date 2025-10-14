<<<<<<< HEAD
from __future__ import annotations
import discord, hashlib
from satpambot.bot.modules.discord_bot.utils.kv_backend import get_kv_for

class StickyEmbed:
    def __init__(self):
        self.kv = get_kv_for("schedule")

    async def ensure(self, channel: discord.TextChannel, title: str) -> discord.Message:
        key = f"sticky:{channel.id}"
        doc = self.kv.get_json(key) or {}
        msg_id = doc.get("msg_id")
        if msg_id:
            try:
                return await channel.fetch_message(int(msg_id))
            except Exception:
                pass
        emb = discord.Embed(title=title, description="Initializing…")
        msg = await channel.send(embed=emb)
        try:
            await msg.pin()
        except Exception:
            pass
        self.kv.set_json(key, {"msg_id": str(msg.id)})
        return msg

    async def update(self, message: discord.Message, embed: discord.Embed):
        await message.edit(embed=embed)

class DedupCache:
    def __init__(self, ttl_seconds: int = 86400):
        self.ttl = int(ttl_seconds)
        self.kv = get_kv_for("dedup")

    def seen(self, signature: str) -> bool:
        key = f"seen:{signature}"
        if self.kv.exists(key):
            return True
        try:
            self.kv.setex(key, self.ttl, "1")
        except Exception:
            self.kv.set_json(key, {"v":"1"})
        return False

    @staticmethod
    def make_sig(*parts: str) -> str:
        h = hashlib.sha256()
        for p in parts:
            h.update((p or "").encode("utf-8", errors="ignore"))
=======

from __future__ import annotations
import discord, time, hashlib
from satpambot.bot.modules.discord_bot.utils.atomic_json import AtomicJsonStore
class StickyEmbed:
    def __init__(self, store_path: str):
        self.store = AtomicJsonStore(store_path); self.store.load()
    async def ensure(self, channel: discord.TextChannel, title: str) -> discord.Message:
        data = self.store.get(); msg_id = data.get('sticky_msg_id')
        if msg_id:
            try: return await channel.fetch_message(int(msg_id))
            except Exception: pass
        emb = discord.Embed(title=title, description='Initializing…')
        msg = await channel.send(embed=emb)
        try: await msg.pin()
        except Exception: pass
        self.store.update(lambda d: d.__setitem__('sticky_msg_id', str(msg.id)))
        return msg
    async def update(self, message: discord.Message, embed: discord.Embed):
        await message.edit(embed=embed)
class DedupCache:
    def __init__(self, store_path: str, ttl_seconds: int = 86400):
        self.store = AtomicJsonStore(store_path); self.store.load(); self.ttl = int(ttl_seconds)
    def _now(self): return int(time.time())
    def seen(self, signature: str) -> bool:
        data = self.store.get().setdefault('seen', {}); now = self._now()
        for k, ts in list(data.items()):
            try:
                if now - int(ts) > self.ttl: del data[k]
            except Exception: del data[k]
        if signature in data:
            self.store.write_atomic(); return True
        data[signature] = str(now); self.store.write_atomic(); return False
    @staticmethod
    def make_sig(*parts: str) -> str:
        h = hashlib.sha256()
        for p in parts: h.update((p or '').encode('utf-8', errors='ignore'))
>>>>>>> 377f4f2 (secure: remove local secrets; add safe example + improved pre-commit)
        return h.hexdigest()
