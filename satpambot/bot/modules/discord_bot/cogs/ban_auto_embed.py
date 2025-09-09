# -*- coding: utf-8 -*-
"""
BanAutoEmbed
- Kirim embed "💀 Ban Otomatis oleh SatpamBot" di channel terakhir user bicara,
  saat terjadi ban (deteksi via on_member_ban + audit log).
- Tidak mirror ke ban log (banlog_route tetap bekerja sendiri).
- Tidak perlu ubah config/loader — file ini akan ter-load otomatis oleh cogs_loader kamu.
"""
from __future__ import annotations
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Optional

import discord
from discord.ext import commands

WIB = timezone(timedelta(hours=7))

def wib_now_str() -> str:
    return datetime.now(WIB).strftime("%Y-%m-%d %H:%M:%S WIB")

class BanAutoEmbed(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Cache channel terakhir tiap user (supaya bisa kirim embed di lokasi pelanggaran)
        self._last_seen_ch: Dict[int, int] = {}
        self._recent_announced: Dict[int, float] = {}  # user_id -> ts

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Simpan channel terakhir user bicara (abaikan bot)
        if message.author and not getattr(message.author, "bot", False):
            self._last_seen_ch[message.author.id] = getattr(message.channel, "id", None)

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        # Debounce: hindari dobel/triple post untuk user sama dalam waktu singkat
        now = asyncio.get_event_loop().time()
        if user.id in self._recent_announced and (now - self._recent_announced[user.id]) < 30:
            return
        self._recent_announced[user.id] = now

        reason: Optional[str] = None
        delete_days: Optional[int] = None

        # Ambil alasan & delete days dari audit log (yang dilakukan oleh bot ini)
        try:
            me = guild.me
            async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.ban):
                if entry.user and me and entry.user.id == me.id and entry.target and entry.target.id == user.id:
                    reason = entry.reason
                    # Beberapa lib expose delete_message_days; fallback None jika tidak ada
                    delete_days = getattr(entry, "delete_message_days", None)
                    break
        except Exception:
            pass

        # Klasifikasi alasan untuk tampilan
        def classify(rs: Optional[str]) -> str:
            if not rs:
                return "Unknown"
            lo = rs.lower()
            if any(k in lo for k in ("nsfw", "porn", "18+", "lewd")):
                return "NSFW"
            if any(k in lo for k in ("phish", "phishing", "scam", "steal", "grabber")):
                return "Phishing"
            return rs

        ch_id = self._last_seen_ch.get(user.id)
        ch: Optional[discord.abc.Messageable] = None
        if ch_id:
            ch = guild.get_channel(ch_id)

        # Bentuk embed
        embed = discord.Embed(
            title="💀 Ban Otomatis oleh SatpamBot",
            description=f"{user.mention} telah diban secara otomatis oleh sistem.",
            color=discord.Color.red(),
        )
        loc_val = ch.mention if isinstance(ch, (discord.TextChannel, discord.Thread)) else "—"
        embed.add_field(name="Lokasi", value=loc_val, inline=False)
        embed.add_field(name="Alasan mencurigakan", value=classify(reason), inline=False)
        if delete_days is not None:
            embed.add_field(name="Purge", value=f"Hapus {delete_days} hari terakhir", inline=False)
        embed.set_footer(text=f"SatpamBot • {wib_now_str()}")

        # Kirim ke channel terakhir user bicara; fallback: tidak kirim (hindari spam server)
        try:
            if ch and hasattr(ch, "send"):
                await ch.send(embed=embed)
        except Exception:
            pass

async def setup(bot: commands.Bot):
    await bot.add_cog(BanAutoEmbed(bot))