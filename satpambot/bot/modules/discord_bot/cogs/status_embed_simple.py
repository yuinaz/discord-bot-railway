
# satpambot/bot/modules/discord_bot/cogs/status_embed_simple.py
from __future__ import annotations

import asyncio
import json
from pathlib import Path as _Path
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from typing import Optional, Dict, Tuple, Iterable

import discord
from discord.ext import commands, tasks

JKT = ZoneInfo("Asia/Jakarta")
MARKER = "SATPAMBOT_STATUS_V1"
STATE_FILE = _Path("/tmp/satpambot_status_msg.json")  # cache message & channel IDs per guild

# === Sticky channel config (hard lock) ===
# Wajib edit ke channel ID tujuan.
STICKY_CHANNEL_ID = 1400375184048787566  # <- sesuai permintaan kamu
# Untuk kompatibilitas nama lama:
STATUS_CHANNEL_ID = STICKY_CHANNEL_ID

PREFERRED_NAMES = ("ngobrol", "general", "bot", "status", "info", "announcements", "errorlog-bot")

def _fmt_uptime(delta: timedelta) -> str:
    secs = int(delta.total_seconds())
    d, r = divmod(secs, 86400)
    h, r = divmod(r, 3600)
    m, s = divmod(r, 60)
    parts = []
    if d: parts.append(f"{d}d")
    if h: parts.append(f"{h}h")
    if m: parts.append(f"{m}m")
    parts.append(f"{s}s")
    return " ".join(parts)

def _now_jkt() -> datetime:
    return datetime.now(JKT)

def _presence_str(bot: commands.Bot) -> str:
    s = getattr(bot, "status", discord.Status.online)
    return f"presence={str(s).lower()}"

def _is_marker_message(m: discord.Message) -> bool:
    if not m or not getattr(m, "author", None):
        return False
    if m.author.id != m.guild.me.id:
        return False
    # content marker (old versions might have it in content)
    if MARKER in (m.content or ""):
        return True
    # or footer marker
    for e in (m.embeds or []):
        try:
            if e.footer and e.footer.text and MARKER in e.footer.text:
                return True
        except Exception:
            pass
    return False

def _load_state() -> Dict[str, Dict[str, int]]:
    try:
        data = json.loads(STATE_FILE.read_text())
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}

def _save_state(d: Dict[str, Dict[str, int]]) -> None:
    try:
        STATE_FILE.write_text(json.dumps(d))
    except Exception:
        pass

def _get_cached(guild_id: int) -> Tuple[Optional[int], Optional[int]]:
    st = _load_state()
    k = str(guild_id)
    if k in st:
        ch = st[k].get("channel_id")
        mid = st[k].get("message_id")
        return (int(ch) if ch else None, int(mid) if mid else None)
    return (None, None)

def _set_cached(guild_id: int, channel_id: int, message_id: int) -> None:
    st = _load_state()
    st[str(guild_id)] = {"channel_id": int(channel_id), "message_id": int(message_id)}
    _save_state(st)

class StatusEmbedSimple(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.start_time = datetime.now(timezone.utc)
        self._update_task.start()

    def cog_unload(self) -> None:
        if self._update_task.is_running():
            self._update_task.cancel()

    # ---- channel & message discovery ----
    async def _iter_candidate_channels(self, g: discord.Guild) -> Iterable[discord.TextChannel]:
        """Yield likely channels to post the status in a stable order.
           Karena STICKY_CHANNEL_ID di-set, kita *hanya* pakai channel itu jika ada permission.
        """
        me = g.me
        if not me:
            return
        # 0) sticky / fixed ONLY
        if STATUS_CHANNEL_ID:
            ch = g.get_channel(int(STATUS_CHANNEL_ID))
            if isinstance(ch, discord.TextChannel) and ch.permissions_for(me).send_messages:
                yield ch
            return  # hard lock: jangan coba channel lain

        # (fallback jika STICKY 0) — urutan kandidat biasa
        cached_ch_id, _ = _get_cached(g.id)
        if cached_ch_id:
            ch = g.get_channel(int(cached_ch_id))
            if isinstance(ch, discord.TextChannel) and ch.permissions_for(me).send_messages:
                yield ch
        if isinstance(g.system_channel, discord.TextChannel) and g.system_channel.permissions_for(me).send_messages:
            yield g.system_channel
        by_name = sorted((c for c in g.text_channels if c.permissions_for(me).send_messages),
                         key=lambda c: (0 if any(n in c.name.lower() for n in PREFERRED_NAMES) else 1, c.position))
        for ch in by_name:
            yield ch

    async def _find_existing_anywhere(self, g: discord.Guild) -> Optional[Tuple[discord.TextChannel, discord.Message]]:
        """Search pins and recent history across candidate channels (which is just sticky channel in hard lock)."""
        async for ch in self._iter_candidate_channels(g):
            # try cached message id first
            _, cached_mid = _get_cached(g.id)
            if cached_mid:
                try:
                    m = await ch.fetch_message(int(cached_mid))
                    if _is_marker_message(m):
                        return ch, m
                except Exception:
                    pass
            # pins
            try:
                pins = await ch.pins()
                for m in pins:
                    if _is_marker_message(m):
                        return ch, m
            except Exception:
                pass
            # history (limit 50)
            try:
                async for m in ch.history(limit=50):
                    if _is_marker_message(m):
                        return ch, m
            except Exception:
                pass
        return None

    async def _ensure_message(self, g: discord.Guild) -> Optional[Tuple[discord.TextChannel, discord.Message]]:
        found = await self._find_existing_anywhere(g)
        if found:
            ch, msg = found
            _set_cached(g.id, ch.id, msg.id)
            try:
                if not msg.pinned:
                    await msg.pin(reason="Pin status embed")
            except Exception:
                pass
            return ch, msg

        async for ch in self._iter_candidate_channels(g):
            try:
                emb, content = self._build_embed_and_content(g)
                msg = await ch.send(content=content, embed=emb, allowed_mentions=discord.AllowedMentions.none())
                try:
                    await msg.pin(reason="Pin status embed")
                except Exception:
                    pass
                _set_cached(g.id, ch.id, msg.id)
                return ch, msg
            except Exception:
                continue
        return None

    # ---- embed ----
    def _build_embed_and_content(self, g: discord.Guild) -> Tuple[discord.Embed, str]:
        now = _now_jkt()
        uptime = _fmt_uptime(datetime.now(timezone.utc) - self.start_time)

        e = discord.Embed(
            title="SatpamBot Status",
            description="Status ringkas bot.",
            color=0x2ecc71,
            timestamp=now,
        )
        e.add_field(name="Akun", value=f"{self.bot.user}", inline=False)
        e.add_field(name="Presence", value=f"`{_presence_str(self.bot)}`", inline=True)
        e.add_field(name="Uptime", value=f"`{uptime}`", inline=True)
        try:
            avatar_url = self.bot.user.display_avatar.url  # discord.py 2.x
        except Exception:
            avatar_url = discord.Embed.Empty
        e.set_footer(text=f"{MARKER} • WIB", icon_url=avatar_url)

        content = f"✅ Online sebagai **{self.bot.user}** | `{_presence_str(self.bot)}` | `uptime={uptime}`"
        content = f"{content}\n{MARKER}"
        return e, content

    # ---- updater ----
    @tasks.loop(seconds=60)
    async def _update_task(self):
        try:
            for g in list(self.bot.guilds):
                pair = await self._ensure_message(g)
                if not pair:
                    continue
                ch, msg = pair
                emb, content = self._build_embed_and_content(g)
                try:
                    await msg.edit(content=content, embed=emb, allowed_mentions=discord.AllowedMentions.none())
                except discord.NotFound:
                    _set_cached(g.id, ch.id, 0)
                except Exception:
                    pass
        except Exception:
            pass

    @_update_task.before_loop
    async def _before(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(2)

async def setup(bot: commands.Bot):
    await bot.add_cog(StatusEmbedSimple(bot))
