
from __future__ import annotations

import asyncio
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo
from typing import Optional

import discord
from discord.ext import commands, tasks

JKT = ZoneInfo("Asia/Jakarta")
MARKER = "SATPAMBOT_STATUS_V1"

def _fmt_uptime(delta: timedelta) -> str:
    secs = int(delta.total_seconds())
    if secs < 0: secs = 0
    d, r = divmod(secs, 86400)
    h, r = divmod(r, 3600)
    m, s = divmod(r, 60)
    parts = []
    if d: parts.append(f"{d}d")
    if h: parts.append(f"{h}h")
    if m: parts.append(f"{m}m")
    if not parts:
        parts.append(f"{s}s")
    else:
        if d == h == 0 and m < 2: parts.append(f"{s}s")
    return " ".join(parts)

class StatusEmbedSimple(commands.Cog):
    """Keep a single sticky status embed in a channel and update it periodically.
    - Always edits the previous message with MARKER (pins preferred).
    - Time displayed in Asia/Jakarta (WIB+7).
    - No config changes required; honors STICKY_CHANNEL_ID if present, else falls back to LOG_CHANNEL_ID/LOG_CHANNEL_ID_RAW.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.start_utc = datetime.now(timezone.utc)
        self.channel_id = self._resolve_channel_id()
        self._cached_message_id: Optional[int] = None
        self._update_task.start()

    # ---------- helpers ----------
    def _resolve_channel_id(self) -> Optional[int]:
        import os
        cid = os.getenv("STICKY_CHANNEL_ID") or os.getenv("LOG_CHANNEL_ID") or os.getenv("LOG_CHANNEL_ID_RAW")
        try:
            return int(cid) if cid else None
        except Exception:
            return None

    def _build_payload(self) -> tuple[str, discord.Embed]:
        presence_txt = "online"
        try:
            if getattr(self.bot, "status", None):
                presence_txt = str(self.bot.status).replace("Status.", "")
        except Exception:
            pass

        up = datetime.now(timezone.utc) - self.start_utc
        uptime_str = _fmt_uptime(up)

        now_jkt = datetime.now(JKT)
        footer = f"{MARKER} • {now_jkt.strftime('%A %d %b %Y %H:%M %Z')}"

        content = f"✅ Online sebagai **{self.bot.user}** | `presence={presence_txt}` | `uptime={uptime_str}`"

        emb = discord.Embed(title="SatpamBot Status", description="Status ringkas bot.", color=0x22C55E)
        emb.add_field(name="Akun", value=str(self.bot.user), inline=False)
        emb.add_field(name="Presence", value=f"`presence={presence_txt}`", inline=True)
        emb.add_field(name="Uptime", value=f"`{uptime_str}`", inline=True)
        emb.set_footer(text=footer)
        emb.timestamp = datetime.now(timezone.utc)
        return content, emb

    async def _get_channel(self) -> Optional[discord.TextChannel]:
        if not self.channel_id:
            return None
        ch = self.bot.get_channel(self.channel_id)
        if isinstance(ch, discord.TextChannel):
            return ch
        try:
            ch = await self.bot.fetch_channel(self.channel_id)
            if isinstance(ch, discord.TextChannel):
                return ch
        except Exception:
            return None
        return None

    async def _find_existing(self, ch: discord.TextChannel) -> Optional[discord.Message]:
        if self._cached_message_id:
            try:
                msg = await ch.fetch_message(self._cached_message_id)
                return msg
            except Exception:
                self._cached_message_id = None

        try:
            for m in await ch.pins():
                if m.author.id == self.bot.user.id:
                    if MARKER in (m.content or ""):
                        self._cached_message_id = m.id
                        return m
                    if m.embeds and any((e.footer and e.footer.text and MARKER in e.footer.text) for e in m.embeds):
                        self._cached_message_id = m.id
                        return m
        except Exception:
            pass

        try:
            async for m in ch.history(limit=30):
                if m.author.id != self.bot.user.id:
                    continue
                if MARKER in (m.content or ""):
                    self._cached_message_id = m.id
                    return m
                if m.embeds and any((e.footer and e.footer.text and MARKER in e.footer.text) for e in m.embeds):
                    self._cached_message_id = m.id
                    return m
        except Exception:
            pass
        return None

    async def _ensure_message(self, ch: discord.TextChannel) -> discord.Message:
        msg = await self._find_existing(ch)
        if msg:
            return msg
        content, emb = self._build_payload()
        msg = await ch.send(content=content, embed=emb, allowed_mentions=discord.AllowedMentions.none())
        try:
            await msg.pin()
        except Exception:
            pass
        self._cached_message_id = msg.id
        return msg

    async def _tick(self):
        ch = await self._get_channel()
        if not ch:
            return
        msg = await self._ensure_message(ch)
        content, emb = self._build_payload()

        try:
            curr = (msg.content or "") + "|" + (msg.embeds[0].footer.text if msg.embeds and msg.embeds[0].footer else "")
        except Exception:
            curr = (msg.content or "")
        if curr == (content + "|" + (emb.footer.text or "")):
            return

        try:
            await msg.edit(content=content, embed=emb, allowed_mentions=discord.AllowedMentions.none())
        except discord.NotFound:
            self._cached_message_id = None
            msg = await self._ensure_message(ch)
            await msg.edit(content=content, embed=emb, allowed_mentions=discord.AllowedMentions.none())
        except Exception:
            pass

    @tasks.loop(seconds=60.0)
    async def _update_task(self):
        await self._tick()

    @_update_task.before_loop
    async def _before(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(2)
        try:
            await self._tick()
        except Exception:
            pass

async def setup(bot: commands.Bot):
    await bot.add_cog(StatusEmbedSimple(bot))
