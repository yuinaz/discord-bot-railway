
import os
import json
import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
import discord
from discord.ext import tasks, commands

# === Cross-process leader lock ===
LOCK_DIR = Path("data/sticky")
LOCK_FILE = LOCK_DIR / "leader.lock"
LOCK_STALE_SEC = 180  # 3 minutes
LOCK_RENEW_SEC = 30

STORE_PATH = Path("data/sticky/sticky.json")
TZ_WIB = timezone(timedelta(hours=7))  # UTC+7

STATUS_SIGNATURE = "SATPAMBOT_STATUS_V1"
LATENCY_SIGNATURE = "SATPAMBOT_LATENCY_V1"

def _now_utc():
    return datetime.now(timezone.utc)

def _load_store():
    try:
        if STORE_PATH.exists():
            return json.loads(STORE_PATH.read_text("utf-8"))
    except Exception:
        pass
    return {"status": {}, "latency": {}}

def _save_store(data):
    try:
        STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
        STORE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass

def _format_uptime(start):
    delta = _now_utc() - start
    sec = int(delta.total_seconds())
    m, s = divmod(sec, 60); h, m = divmod(m, 60); d, h = divmod(h, 24)
    parts = []
    if d: parts.append(f"{d}d")
    if h: parts.append(f"{h}h")
    if m: parts.append(f"{m}m")
    parts.append(f"{s}s")
    return " ".join(parts)

class StickyStatus(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.start_at = _now_utc()
        self.store = _load_store()
        self.pref_name = os.getenv("STICKY_CHANNEL_NAME", "log-botphising").strip("# ").lower()

        # optional explicit ids
        def _ids(env):
            raw = os.getenv(env, "")
            out = set()
            for t in raw.replace(";", ",").split(","):
                t = t.strip()
                if not t:
                    continue
                try: out.add(int(t))
                except: pass
            return out

        both = _ids("STICKY_CHANNEL_ID")
        self.status_ids = _ids("STICKY_STATUS_CHANNEL_IDS") or set(both)
        self.latency_ids = _ids("STICKY_LATENCY_CHANNEL_IDS") or set(both)

        self._lock = asyncio.Lock()
        self._last_edit = {"status": {}, "latency": {}}
        self._leader = False
        self._leader_task = None

    @commands.Cog.listener()
    async def on_ready(self):
        await self._resolve_default_channels()
        await self._elect_leader()
        if self._leader:
            await self._ensure_messages()
            if not self.status_loop.is_running():
                self.status_loop.start()
            if not self.latency_loop.is_running():
                self.latency_loop.start()

    async def _resolve_default_channels(self):
        if self.status_ids and self.latency_ids:
            return
        for g in self.bot.guilds:
            me = g.me
            for ch in g.text_channels:
                try:
                    if ch.name.lower() == self.pref_name and ch.permissions_for(me).send_messages:
                        self.status_ids.add(ch.id)
                        self.latency_ids.add(ch.id)
                        return
                except Exception:
                    continue

    # ---------- Leader election (file lock) ----------
    async def _elect_leader(self):
        if os.getenv("STICKY_NO_LOCK"):
            self._leader = True
            return
        LOCK_DIR.mkdir(parents=True, exist_ok=True)
        pid = os.getpid()
        while True:
            try:
                if not LOCK_FILE.exists():
                    LOCK_FILE.write_text(json.dumps({"pid": pid, "ts": _now_utc().isoformat()}), encoding="utf-8")
                    self._leader = True
                    break
                else:
                    data = json.loads(LOCK_FILE.read_text("utf-8"))
                    ts = datetime.fromisoformat(data.get("ts","").replace("Z","+00:00")) if data.get("ts") else None
                    if not ts or (_now_utc() - ts).total_seconds() > LOCK_STALE_SEC:
                        # stale -> take over
                        LOCK_FILE.write_text(json.dumps({"pid": pid, "ts": _now_utc().isoformat()}), encoding="utf-8")
                        self._leader = True
                        break
                    else:
                        self._leader = (data.get("pid") == pid)
                        if self._leader:
                            break
            except Exception:
                # if anything goes wrong, try to become leader anyway
                self._leader = True
                break
            await asyncio.sleep(2.0)
        if self._leader and (self._leader_task is None or self._leader_task.done()):
            self._leader_task = asyncio.create_task(self._leader_heartbeat())

    async def _leader_heartbeat(self):
        pid = os.getpid()
        while True:
            try:
                LOCK_FILE.write_text(json.dumps({"pid": pid, "ts": _now_utc().isoformat()}), encoding="utf-8")
            except Exception:
                pass
            await asyncio.sleep(LOCK_RENEW_SEC)

    # ---------- Sticky logic ----------
    async def _ensure_messages(self):
        for cid in list(self.status_ids):
            await self._ensure_single(cid, "status")
        for cid in list(self.latency_ids):
            await self._ensure_single(cid, "latency")

    async def _ensure_single(self, channel_id: int, key: str):
        ch = await self._get_channel(channel_id)
        if not ch: return
        await self._scan_and_claim(ch, key)
        dkey = str(channel_id)
        rec = self.store.get(key, {}).get(dkey, {})
        msg_id = rec.get("message_id")
        msg = None
        if msg_id:
            try: msg = await ch.fetch_message(int(msg_id))
            except: msg = None
        if msg is None:
            content, embed = (self._status_payload() if key=="status" else self._latency_payload())
            try:
                m = await ch.send(content=content, embed=embed)
                self.store.setdefault(key, {})[dkey] = {"message_id": m.id, "last_content": content, "last_ts": _now_utc().isoformat()}
                _save_store(self.store)
            except Exception:
                return

    async def _scan_and_claim(self, ch: discord.TextChannel, key: str):
        try: me = ch.guild.me
        except: me = None
        if not me: return
        sign = STATUS_SIGNATURE if key=="status" else LATENCY_SIGNATURE
        newest = None; duplicates = []
        async for m in ch.history(limit=50):
            if m.author != me: continue
            is_ours = False
            if m.embeds:
                e = m.embeds[0]
                if (e.footer and e.footer.text and sign in e.footer.text) or (e.title and "satpambot status" in e.title.lower()):
                    is_ours = True
            if not is_ours and m.content:
                if key=="latency" and "Latency" in m.content and "SatpamBot online" in m.content:
                    is_ours = True
                if key=="status" and m.content.strip().startswith("✅ Online"):
                    is_ours = True
            if is_ours:
                if newest is None: newest = m
                else: duplicates.append(m)
        # delete older duplicates
        for m in duplicates:
            try: await m.delete()
            except: pass
        if newest is not None:
            dkey = str(ch.id)
            self.store.setdefault(key, {})[dkey] = {"message_id": newest.id, "last_content": newest.content or "", "last_ts": _now_utc().isoformat()}
            _save_store(self.store)

    async def _get_channel(self, cid: int):
        ch = self.bot.get_channel(cid)
        if ch is None:
            try: ch = await self.bot.fetch_channel(cid)
            except: return None
        return ch

    def _presence_text(self):
        for g in self.bot.guilds:
            me = g.me
            if me and getattr(me, "status", None) is not None:
                return str(me.status)
        return "online"

    def _status_payload(self):
        u = self.bot.user
        name = f"{u.name}#{u.discriminator}" if u and u.discriminator != "0" else (u.name if u else "Bot")
        presence = self._presence_text()
        uptime = _format_uptime(self.start_at)
        header = f"✅ Online sebagai {name} | presence={presence} | uptime={uptime}"
        e = discord.Embed(
            title="SatpamBot Status",
            description="Status ringkas bot.",
            color=0x30D158,
            timestamp=datetime.now(TZ_WIB),
        )
        e.add_field(name="Akun", value=name, inline=True)
        e.add_field(name="Presence", value=f"``{presence}``", inline=True)
        e.add_field(name="Uptime", value=uptime, inline=True)
        e.set_footer(text=f"{STATUS_SIGNATURE} • WIB (UTC+7)")
        return header, e

    def _latency_payload(self):
        ms = int(round((self.bot.latency or 0.0) * 1000))
        return f"🟢 SatpamBot online • Latency {ms} ms", None

    @tasks.loop(seconds=30.0, reconnect=True)
    async def status_loop(self):
        if not self._leader: return
        for cid in list(self.status_ids):
            await self._edit_once(cid, "status", self._status_payload, min_periodic=120)

    @tasks.loop(seconds=15.0, reconnect=True)
    async def latency_loop(self):
        if not self._leader: return
        for cid in list(self.latency_ids):
            await self._edit_once(cid, "latency", self._latency_payload, min_periodic=120, latency_mode=True)

    async def _edit_once(self, cid: int, key: str, payload_fn, min_periodic=120, latency_mode=False):
        async with self._lock:
            ch = await self._get_channel(cid)
            if not ch: return
            dkey = str(cid)
            rec = self.store.get(key, {}).get(dkey)
            if not rec:
                await self._ensure_single(cid, key)
                rec = self.store.get(key, {}).get(dkey)
                if not rec: return
            try:
                msg = await ch.fetch_message(int(rec["message_id"]))
            except Exception:
                await self._ensure_single(cid, key)
                try: msg = await ch.fetch_message(int(self.store[key][dkey]["message_id"]))
                except Exception: return
            new_content, new_embed = payload_fn()
            prev_content = rec.get("last_content","")
            should = True
            if latency_mode:
                import re as _re
                def _ms(s):
                    m = _re.search(r"(\d+)\s*ms", s or "")
                    return int(m.group(1)) if m else None
                a, b = _ms(prev_content), _ms(new_content)
                if a is not None and b is not None:
                    delta, pct = abs(b-a), abs(b-a)/max(a,1)
                    should = (delta >= 50) or (pct >= 0.10)
            # periodic refresh
            last_ts = rec.get("last_ts")
            if last_ts:
                try:
                    last = datetime.fromisoformat(last_ts.replace("Z","+00:00"))
                    age = (_now_utc() - last).total_seconds()
                    if age < min_periodic and not should:
                        return
                except: pass
            try:
                await msg.edit(content=new_content, embed=new_embed)
                rec["last_content"] = new_content
                rec["last_ts"] = _now_utc().isoformat()
                self.store[key][dkey] = rec
                _save_store(self.store)
            except Exception:
                pass

async def setup(bot: commands.Bot):
    await bot.add_cog(StickyStatus(bot))
