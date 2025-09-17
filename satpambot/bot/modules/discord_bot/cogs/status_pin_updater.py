# satpambot/bot/modules/discord_bot/cogs/status_pin_updater.py
"""
StatusPinUpdater (ENV-aware, NO-CREATE)
- Hanya mengedit pesan status yang sudah ada (footer `SATPAMBOT_STATUS_V1`), tidak pernah membuat baru.
- Jika ENV ID channel tersedia, gunakan itu; jika tidak, gunakan pola nama (fallback).
ENV (opsional):
  - STATUS_CHANNEL_ID / LOG_CHANNEL_ID / LOG_BOTPHISING_ID / LOG_BOTPHISHING_ID
  - STATUS_CHANNEL_NAME / LOG_CHANNEL_NAME
Interval update: 5 menit.
"""
from __future__ import annotations
import os, json, logging, re, time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional
import discord
from discord.ext import commands, tasks

log = logging.getLogger(__name__)

def _env_channel_id() -> Optional[int]:
    for key in ("STATUS_CHANNEL_ID","LOG_CHANNEL_ID","LOG_BOTPHISING_ID","LOG_BOTPHISHING_ID"):
        v = os.getenv(key)
        if v and v.strip().isdigit():
            return int(v.strip())
    return None

def _env_channel_name_patterns() -> List[str]:
    pats: List[str] = []
    for key in ("STATUS_CHANNEL_NAME","LOG_CHANNEL_NAME"):
        v = os.getenv(key)
        if v:
            import re as _re
            pats.append(_re.escape(v.strip()))
    return pats

FORCE_CHANNEL_ID: Optional[int] = _env_channel_id()
FORCE_CHANNEL_NAME_PATTERNS: List[str] = (
    _env_channel_name_patterns()
    or [r"log[-_ ]?botphish(?:ing|ing)?", r"log[-_ ]?botphis(?:ing|hing)?"]
)
PIN_TAG = "SATPAMBOT_STATUS_V1"
STORE_PATH = Path("data/satpambot_status_pin.json")

@dataclass
class StatusRecord:
    channel_id: int
    message_id: int

class StatusPinUpdater(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._started_at = time.time()
        self._store: Dict[str, StatusRecord] = {}
        self._load_store()
        self.ticker.start()

    def _load_store(self) -> None:
        try:
            if STORE_PATH.exists():
                data = json.loads(STORE_PATH.read_text(encoding="utf-8") or "{}")
                self._store = {gid: StatusRecord(**rec) for gid, rec in data.items()}
        except Exception as e:
            log.warning("[status-pin] load store failed: %r", e)

    def _save_store(self) -> None:
        try:
            STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
            data = {gid: rec.__dict__ for gid, rec in self._store.items()}
            STORE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            log.warning("[status-pin] save store failed: %r", e)

    def _build_embed(self) -> discord.Embed:
        presence = "presence=online"
        up = int(time.time() - self._started_at)
        m, s = divmod(up, 60); h, m = divmod(m, 60)
        up_str = f"{h}h {m}m {s}s" if h else f"{m}m {s}s"
        emb = discord.Embed(title="SatpamBot Status", description="Status ringkas bot.", color=0x2ECC71)
        emb.add_field(name="Akun", value=str(self.bot.user), inline=False)
        emb.add_field(name="Presence", value=presence, inline=True)
        emb.add_field(name="Uptime", value=up_str, inline=True)
        emb.set_footer(text=PIN_TAG)
        return emb

    async def _find_existing_message(self, ch: discord.TextChannel) -> Optional[discord.Message]:
        try:
            pins = await ch.pins()
            for m in pins:
                for e in m.embeds or []:
                    if e.footer and PIN_TAG in (e.footer.text or ""):
                        return m
        except Exception:
            pass
        try:
            async for m in ch.history(limit=80, oldest_first=False):
                for e in m.embeds or []:
                    if e.footer and PIN_TAG in (e.footer.text or ""):
                        return m
        except Exception:
            pass
        return None

    def _match_name(self, name: str) -> bool:
        low = (name or "").lower()
        return any(re.search(p, low) for p in FORCE_CHANNEL_NAME_PATTERNS)

    async def _resolve_channel(self, guild: discord.Guild) -> Optional[discord.TextChannel]:
        if FORCE_CHANNEL_ID:
            ch = guild.get_channel(FORCE_CHANNEL_ID) or await self.bot.fetch_channel(FORCE_CHANNEL_ID)
            if isinstance(ch, discord.TextChannel):
                return ch
        for ch in getattr(guild, "text_channels", []):
            if isinstance(ch, discord.TextChannel) and self._match_name(ch.name):
                return ch
        return None

    async def _ensure_message(self, guild: discord.Guild) -> Optional[discord.Message]:
        rec = self._store.get(str(guild.id))
        if rec:
            ch = guild.get_channel(rec.channel_id) or await self.bot.fetch_channel(rec.channel_id)
            if isinstance(ch, discord.TextChannel):
                try:
                    return await ch.fetch_message(rec.message_id)
                except Exception:
                    pass
        ch = await self._resolve_channel(guild)
        if not ch:
            return None
        msg = await self._find_existing_message(ch)
        if msg:
            if not msg.pinned:
                try: await msg.pin(reason="SatpamBot status pin (ensure)")
                except Exception: pass
            self._store[str(guild.id)] = StatusRecord(channel_id=ch.id, message_id=msg.id)
            self._save_store()
            return msg
        return None

    async def _update_message(self, msg: discord.Message) -> None:
        try:
            await msg.edit(embed=self._build_embed())
            if not msg.pinned:
                try: await msg.pin(reason="SatpamBot status pin (update)")
                except Exception: pass
        except Exception as e:
            log.warning("[status-pin] edit failed: %r", e)

    @tasks.loop(minutes=5.0)
    async def ticker(self):
        await self.bot.wait_until_ready()
        for g in list(self.bot.guilds):
            try:
                m = await self._ensure_message(g)
                if m:
                    await self._update_message(m)
            except Exception as e:
                log.warning("[status-pin] tick error (guild %s): %r", getattr(g, "id", "?"), e)

    @ticker.before_loop
    async def before_ticker(self):
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot):
    await bot.add_cog(StatusPinUpdater(bot))
