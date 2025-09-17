# satpambot/bot/modules/discord_bot/cogs/status_pin_updater.py
# Versi: 5-min update
from __future__ import annotations
import asyncio, json, logging, re, time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, List
import discord
from discord.ext import commands, tasks

log = logging.getLogger(__name__)

ALLOWED_CHANNEL_NAME_PATTERNS: List[str] = [r"status", r"satpambot.*status"]
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

    def _load_store(self):
        try:
            if STORE_PATH.exists():
                data = json.loads(STORE_PATH.read_text(encoding="utf-8") or "{}")
                self._store = {gid: StatusRecord(**rec) for gid, rec in data.items()}
        except Exception as e:
            log.warning("[status-pin] load store failed: %r", e)

    def _save_store(self):
        try:
            STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
            data = {gid: rec.__dict__ for gid, rec in self._store.items()}
            STORE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            log.warning("[status-pin] save store failed: %r", e)

    def _match_channel_name(self, name: str) -> bool:
        low = (name or "").lower()
        return any(re.search(pat, low) for pat in ALLOWED_CHANNEL_NAME_PATTERNS)

    async def _ensure_message(self, guild: discord.Guild) -> Optional[discord.Message]:
        rec = self._store.get(str(guild.id))
        if rec:
            ch = guild.get_channel(rec.channel_id) or await self.bot.fetch_channel(rec.channel_id)
            if isinstance(ch, (discord.TextChannel, discord.Thread)):
                try:
                    return await ch.fetch_message(rec.message_id)
                except Exception:
                    pass
        # pick channel by name
        target = None
        for ch in guild.text_channels:
            try:
                if self._match_channel_name(ch.name) and ch.permissions_for(guild.me or guild.get_member(self.bot.user.id)).send_messages:
                    target = ch; break
            except Exception: pass
        if not target:
            return None
        # find existing by tag
        try:
            async for m in target.history(limit=50, oldest_first=False):
                if any(e.footer and PIN_TAG in (e.footer.text or "") for e in (m.embeds or [])):
                    if not m.pinned:
                        try: await m.pin(reason="SatpamBot status pin")
                        except Exception: pass
                    self._store[str(guild.id)] = StatusRecord(channel_id=target.id, message_id=m.id)
                    self._save_store()
                    return m
        except Exception: pass
        # create new
        msg = await target.send(embed=self._build_embed())
        try: await msg.pin(reason="SatpamBot status pin")
        except Exception: pass
        self._store[str(guild.id)] = StatusRecord(channel_id=target.id, message_id=msg.id)
        self._save_store()
        return msg

    def _build_embed(self) -> discord.Embed:
        presence = "presence=online"
        up = int(time.time() - self._started_at)
        m, s = divmod(up, 60); h, m = divmod(m, 60)
        up_str = f"{h}h {m}m {s}s" if h else f"{m}m {s}s"
        title = f"✅ Online sebagai {self.bot.user} | {presence} | uptime={up_str}"
        emb = discord.Embed(title="SatpamBot Status", description="Status ringkas bot.", color=0x2ECC71)
        emb.add_field(name="Akun", value=str(self.bot.user), inline=False)
        emb.add_field(name="Presence", value=presence, inline=True)
        emb.add_field(name="Uptime", value=up_str, inline=True)
        emb.set_footer(text=PIN_TAG)
        return emb

    async def _update_message(self, msg: discord.Message):
        try:
            await msg.edit(embed=self._build_embed())
            if not msg.pinned:
                try: await msg.pin(reason="SatpamBot status pin (update)")
                except Exception: pass
        except Exception as e:
            log.warning("[status-pin] edit failed: %r", e)

    @tasks.loop(minutes=5.0)  # disamakan dengan interval UptimeRobot (5 menit)
    async def ticker(self):
        await self.bot.wait_until_ready()
        for g in list(self.bot.guilds):
            try:
                m = await self._ensure_message(g)
                if m: await self._update_message(m)
            except Exception as e:
                log.warning("[status-pin] tick error (guild %s): %r", getattr(g, "id", "?"), e)

    @ticker.before_loop
    async def before_ticker(self):
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot):
    await bot.add_cog(StatusPinUpdater(bot))
