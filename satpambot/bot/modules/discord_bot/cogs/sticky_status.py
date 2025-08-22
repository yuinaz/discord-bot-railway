
import os
import json
import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
import discord
from discord.ext import tasks, commands

STORE_PATH = Path("data/sticky/sticky.json")
TZ_WIB = timezone(timedelta(hours=7))  # UTC+7

STATUS_SIGNATURE = "SATPAMBOT_STATUS_V1"
LATENCY_SIGNATURE = "SATPAMBOT_LATENCY_V1"

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

def _parse_ids(name: str):
    raw = os.getenv(name, "").strip()
    if not raw:
        return set()
    out = set()
    for tok in raw.replace(";", ",").split(","):
        tok = tok.strip()
        if not tok:
            continue
        try:
            out.add(int(tok))
        except Exception:
            pass
    return out

def _format_uptime(start: datetime) -> str:
    delta = datetime.now(timezone.utc) - start
    seconds = int(delta.total_seconds())
    m, s = divmod(seconds, 60); h, m = divmod(m, 60); d, h = divmod(h, 24)
    parts = []
    if d: parts.append(f"{d}d")
    if h: parts.append(f"{h}h")
    if m: parts.append(f"{m}m")
    parts.append(f"{s}s")
    return " ".join(parts)

class StickyStatus(commands.Cog):
    """Exclusive sticky (single message per type) with WIB & anti-spam."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.start_at = datetime.now(timezone.utc)
        self.store = _load_store()

        # Channel resolution
        self.pref_name = os.getenv("STICKY_CHANNEL_NAME", "log-botphising").strip("# ").lower()
        both = _parse_ids("STICKY_CHANNEL_ID")
        self.status_ids = _parse_ids("STICKY_STATUS_CHANNEL_IDS") or set(both)
        self.latency_ids = _parse_ids("STICKY_LATENCY_CHANNEL_IDS") or set(both)

        # Internal locks/cooldowns
        self._lock = asyncio.Lock()
        self._last_edit = {"status": {}, "latency": {}}  # channel_id -> ts

    @commands.Cog.listener()
    async def on_ready(self):
        await self._resolve_default_channel_if_needed()
        await self._ensure_messages()
        if not self.status_loop.is_running():
            self.status_loop.start()
        if not self.latency_loop.is_running():
            self.latency_loop.start()

    async def _resolve_default_channel_if_needed(self):
        if self.status_ids or self.latency_ids:
            return
        for g in self.bot.guilds:
            me = g.me
            for ch in g.text_channels:
                try:
                    if ch.name.lower() == self.pref_name and ch.permissions_for(me).send_messages:
                        cid = ch.id
                        self.status_ids.add(cid)
                        self.latency_ids.add(cid)
                        return
                except Exception:
                    continue

    async def _ensure_messages(self):
        await self.bot.wait_until_ready()
        for cid in set(self.status_ids):
            await self._ensure_single(cid, key="status")
        for cid in set(self.latency_ids):
            await self._ensure_single(cid, key="latency")

    async def _ensure_single(self, channel_id: int, key: str):
        ch = await self._get_channel(channel_id)
        if ch is None:
            return
        dkey = str(channel_id)
        self.store.setdefault(key, {})
        rec = self.store[key].get(dkey) or {}
        # First, scan channel to claim newest and delete older duplicates
        await self._scan_and_claim(ch, key)
        # After scan, try to fetch current msg
        rec = self.store[key].get(dkey) or {}
        msg_id = rec.get("message_id")
        msg = None
        if msg_id:
            try:
                msg = await ch.fetch_message(int(msg_id))
            except Exception:
                msg = None
        if msg is None:
            content, embed = (self._status_payload() if key == "status" else self._latency_payload(rec))
            try:
                msg = await ch.send(content=content, embed=embed)
                self.store[key][dkey] = {"message_id": msg.id, "last_content": content, "last_ts": datetime.now(timezone.utc).isoformat()}
                _save_store(self.store)
            except Exception:
                return

    async def _scan_and_claim(self, ch: discord.TextChannel, key: str):
        """Find our own sticky messages in the channel. Keep the newest; delete older duplicates.
        This enforces single-message per type even if legacy cogs had posted before."""
        try:
            me = ch.guild.me
        except Exception:
            me = None
        if me is None:
            return
        sign = STATUS_SIGNATURE if key == "status" else LATENCY_SIGNATURE
        newest = None
        to_delete = []
        async for m in ch.history(limit=50):
            if m.author != me:  # only touch our own messages
                continue
            found = False
            if key == "status":
                # status: either embed title "SatpamBot Status" OR footer contains signature OR content starts with ✅ Online
                if m.embeds:
                    e = m.embeds[0]
                    if (e.title and "satpambot status" in e.title.lower()) or (e.footer and e.footer.text and sign in e.footer.text):
                        found = True
                if not found and m.content and m.content.strip().startswith("✅"):
                    found = True
            else:
                # latency: content starts with the green dot OR footer signature
                if m.content and "Latency" in m.content and "online" in m.content:
                    found = True
                if not found and m.embeds:
                    e = m.embeds[0]
                    if e.footer and e.footer.text and sign in e.footer.text:
                        found = True
            if found:
                if newest is None:
                    newest = m
                else:
                    to_delete.append(m)
        # Keep newest; delete others
        try:
            for m in to_delete:
                await m.delete()
        except Exception:
            pass
        if newest is not None:
            dkey = str(ch.id)
            self.store.setdefault(key, {})
            self.store[key][dkey] = {"message_id": newest.id, "last_content": newest.content or "", "last_ts": datetime.now(timezone.utc).isoformat()}
            _save_store(self.store)

    async def _get_channel(self, channel_id: int):
        ch = self.bot.get_channel(channel_id)
        if ch is None:
            try:
                ch = await self.bot.fetch_channel(channel_id)
            except Exception:
                return None
        return ch

    def _presence_text(self):
        for g in self.bot.guilds:
            me = g.me
            if me and getattr(me, "status", None) is not None:
                return str(me.status)
        return "online"

    def _status_payload(self):
        user = self.bot.user
        name = f"{user.name}#{user.discriminator}" if user and user.discriminator != '0' else (user.name if user else "Bot")
        presence = self._presence_text()
        uptime = _format_uptime(self.start_at)
        header = f"✅ Online sebagai {name} | presence={presence} | uptime={uptime}"
        embed = discord.Embed(
            title="SatpamBot Status",
            description="Status ringkas bot.",
            color=0x30D158,
            timestamp=datetime.now(TZ_WIB)
        )
        embed.add_field(name="Akun", value=name, inline=True)
        embed.add_field(name="Presence", value=f"``{presence}``", inline=True)
        embed.add_field(name="Uptime", value=uptime, inline=True)
        embed.set_footer(text=f"{STATUS_SIGNATURE} • WIB (UTC+7)")
        return header, embed

    def _latency_payload(self, rec=None):
        ms = int(round((self.bot.latency or 0.0) * 1000))
        text = f"🟢 SatpamBot online • Latency {ms} ms"
        # Put signature in footer-less content mode by returning embed=None; store compared by content
        return text, None

    # --- loops (with anti-spam + cooldown) ---
    @tasks.loop(seconds=30.0, reconnect=True)
    async def status_loop(self):
        for cid in set(self.status_ids):
            await self._edit_once(cid, key="status", payload_func=self._status_payload, min_periodic=120)

    @tasks.loop(seconds=15.0, reconnect=True)
    async def latency_loop(self):
        for cid in set(self.latency_ids):
            await self._edit_once(cid, key="latency", payload_func=lambda: self._latency_payload(self._get_rec('latency', cid)), min_periodic=120, latency_mode=True)

    def _get_rec(self, key, channel_id):
        return self.store.get(key, {}).get(str(channel_id))

    async def _edit_once(self, channel_id: int, key: str, payload_func, min_periodic: int = 120, latency_mode: bool = False):
        async with self._lock:
            ch = await self._get_channel(channel_id)
            if ch is None:
                return
            dkey = str(channel_id)
            rec = self.store.get(key, {}).get(dkey)
            if not rec or not rec.get("message_id"):
                await self._ensure_single(channel_id, key=key)
                rec = self.store.get(key, {}).get(dkey)
                if not rec:  # still none
                    return
            try:
                msg = await ch.fetch_message(int(rec["message_id"]))
            except Exception:
                # attempt reclaim (legacy cog may have created new one)
                await self._ensure_single(channel_id, key=key)
                try:
                    msg = await ch.fetch_message(int(self.store[key][dkey]["message_id"]))
                except Exception:
                    return

            new_content, new_embed = payload_func()

            # Anti-spam check
            prev_content = rec.get("last_content", "")
            last_ts_iso = rec.get("last_ts")
            should = True
            if latency_mode:
                try:
                    import re as _re
                    prev_ms = int(_re.search(r"(\d+)\s*ms", prev_content).group(1)) if prev_content else None
                    new_ms = int(_re.search(r"(\d+)\s*ms", new_content).group(1))
                except Exception:
                    prev_ms, new_ms = None, None
                if prev_ms is not None and new_ms is not None:
                    delta = abs(new_ms - prev_ms)
                    pct = (delta / max(prev_ms, 1)) if prev_ms else 1.0
                    should = (delta >= 50) or (pct >= 0.10)

            # Per-message cooldown (5s) + periodic refresh
            now = datetime.now(timezone.utc)
            last_edit_ts = self._last_edit[key].get(dkey)
            if last_edit_ts and (now - last_edit_ts).total_seconds() < 5 and not should:
                return
            if last_ts_iso:
                try:
                    last_dt = datetime.fromisoformat(last_ts_iso.replace("Z","+00:00"))
                except Exception:
                    last_dt = None
                if last_dt:
                    age = (now - last_dt).total_seconds()
                    if age < min_periodic and not should:
                        return

            # Perform edit
            try:
                await msg.edit(content=new_content, embed=new_embed)
                rec["last_content"] = new_content
                rec["last_ts"] = now.isoformat()
                self.store[key][dkey] = rec
                _save_store(self.store)
                self._last_edit[key][dkey] = now
            except discord.HTTPException as e:
                if getattr(e, "status", None) in (403, 404):
                    await self._ensure_single(channel_id, key=key)
            except Exception:
                pass

async def setup(bot: commands.Bot):
    await bot.add_cog(StickyStatus(bot))
