
# -*- coding: utf-8 -*-
"""
Sticky status message (no spam). 
Edits a single status message in the log channel instead of posting new ones.
Drop-in replacement for: satpambot.bot.modules.discord_bot.cogs.status_sticky_patched
"""
from __future__ import annotations

import os
import math
import asyncio
from datetime import datetime, timezone
from typing import Optional

import discord
from discord.ext import commands, tasks

# Optional helper (if exists in your tree)
try:
    from satpambot.bot.modules.discord_bot.helpers import log_utils  # type: ignore
except Exception:  # pragma: no cover
    log_utils = None  # fallback below


MARKER = "SATPAMBOT_STATUS_V1"  # used in embed footer to find the sticky message
UPDATE_SECONDS = int(os.environ.get("STATUS_UPDATE_SECONDS", "60"))  # no env change needed; default 60s


def _is_finite_float(x: float) -> bool:
    try:
        return math.isfinite(x)
    except Exception:
        return False


class StickyStatus(commands.Cog):
    """Keep a single edited status message in the log channel."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._channel_id: Optional[int] = None
        self._message_id: Optional[int] = None
        self._last_payload: Optional[str] = None  # prevent redundant edits

    # -------- utilities

    def _choose_channel(self) -> Optional[discord.TextChannel]:
        # 1) env id (prefer LOG_CHANNEL_ID to stay compatible with your config)
        raw = os.environ.get("LOG_CHANNEL_ID") or os.environ.get("STATUS_CHANNEL_ID")
        ch: Optional[discord.TextChannel] = None
        if raw:
            try:
                cid = int(str(raw).strip())
                ch = self.bot.get_channel(cid)  # type: ignore
                if ch:
                    return ch
            except Exception:
                pass

        # 2) helper (if available in your tree)
        if log_utils and hasattr(log_utils, "resolve_log_channel"):
            try:
                ch = log_utils.resolve_log_channel(self.bot)  # type: ignore
                if ch:
                    return ch
            except Exception:
                pass

        # 3) by name (fallback)
        fallback_names = [
            os.environ.get("LOG_CHANNEL_NAME") or "log-botphising",
            "log-botphishing",
            "satpambot-log",
        ]
        for guild in list(self.bot.guilds):
            for name in fallback_names:
                c = discord.utils.get(guild.text_channels, name=name)  # type: ignore
                if c:
                    return c  # type: ignore
        return None

    async def _find_or_create_message(self, ch: discord.TextChannel) -> Optional[discord.Message]:
        # if we already know id, try to fetch it
        if self._message_id:
            try:
                msg = await ch.fetch_message(self._message_id)
                return msg
            except Exception:
                self._message_id = None  # fetch failed; fall through to search

        # scan recent history for our marker
        try:
            async for m in ch.history(limit=100):
                if m.author.id == (self.bot.user.id if self.bot.user else 0):
                    # Check marker in embed footer
                    found = False
                    if m.embeds:
                        for e in m.embeds:
                            if e.footer and e.footer.text and MARKER in str(e.footer.text):
                                found = True
                                break
                    # also allow plain content marker (for older posts)
                    if (not found) and MARKER in (m.content or ""):
                        found = True
                    if found:
                        self._message_id = m.id
                        return m
        except Exception:
            pass

        # not found -> create new one
        try:
            msg = await ch.send(content="Initializing status…")
            self._message_id = msg.id
            # pin once (optional "sticky")
            try:
                await msg.pin(reason="SatpamBot • Sticky status")
            except Exception:
                pass
            return msg
        except Exception:
            return None

    def _make_embed(self) -> discord.Embed:
        now = datetime.now(timezone.utc)
        me = str(self.bot.user) if self.bot.user else "SatpamBot"
        # latency
        lat_s = float(getattr(self.bot, "latency", 0.0) or 0.0)
        lat_ms = 0 if not _is_finite_float(lat_s) else int(max(0.0, lat_s * 1000.0))

        e = discord.Embed(
            title="SatpamBot Status",
            description="Ringkasan status bot.",
            colour=discord.Colour.green() if self.bot.is_ready() else discord.Colour.orange(),
            timestamp=now,
        )
        e.add_field(name="Akun", value=f"{me}", inline=False)

        # metrics
        try:
            guilds = len(self.bot.guilds)
        except Exception:
            guilds = 0
        try:
            members = sum(g.member_count or 0 for g in self.bot.guilds)
        except Exception:
            members = 0

        e.add_field(name="Presence", value="presence=online" if self.bot.is_ready() else "starting", inline=True)
        e.add_field(name="Latency", value=f"{lat_ms} ms", inline=True)
        e.add_field(name="Guilds", value=str(guilds), inline=True)
        e.add_field(name="Members", value=str(members), inline=True)

        e.set_footer(text=MARKER)
        return e

    # -------- loop

    @tasks.loop(seconds=UPDATE_SECONDS)
    async def _update_loop(self) -> None:
        ch = self._choose_channel()
        if not ch:
            # log once per minute, no spam
            print("[status_sticky] WARNING: log channel not found")
            return

        msg = await self._find_or_create_message(ch)
        if not msg:
            print("[status_sticky] WARNING: failed to create/find sticky message")
            return

        embed = self._make_embed()
        payload = f"{embed.title}|{embed.colour}|{embed.fields[1].value if embed.fields else ''}"  # small diff key

        # avoid redundant edits
        if self._last_payload == payload:
            return
        self._last_payload = payload

        content = f"✅ SatpamBot online • Latency {embed.fields[1].value} (edited)"
        try:
            await msg.edit(content=content, embed=embed)
        except Exception as exc:
            print(f"[status_sticky] edit failed: {exc!r}")

        # cleanup duplicates (older own status messages with marker)
        try:
            async for m in ch.history(limit=50):
                if m.id == msg.id:
                    continue
                if m.author.id == (self.bot.user.id if self.bot.user else 0):
                    mark_ok = False
                    if m.embeds:
                        for e in m.embeds:
                            if e.footer and e.footer.text and MARKER in str(e.footer.text):
                                mark_ok = True
                                break
                    if mark_ok:
                        try:
                            await m.delete()
                        except Exception:
                            pass
        except Exception:
            pass

    @_update_loop.before_loop
    async def _before(self) -> None:
        await self.bot.wait_until_ready()

    # also kick a first update when ready
    @commands.Cog.listener()
    async def on_ready(self) -> None:
        if not self._update_loop.is_running():
            self._update_loop.start()

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(StickyStatus(bot))
