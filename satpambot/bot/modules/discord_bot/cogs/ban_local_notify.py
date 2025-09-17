# satpambot/bot/modules/discord_bot/cogs/ban_local_notify.py
"""
BanLocalNotify (no ENV) — kirim embed ban di channel tempat user pertama kali kirim pesan.
- Simpan "first touchdown" (user_id -> (channel_id, message_id)) via on_message (TTL 10 menit).
- Saat on_member_ban: kirim embed ke channel/thread itu (fallback diam kalau tidak ada izin).
- Anti spam: satu notif per user per ban.
- Tidak mengubah pipeline ban utama (ban_logger, dsb).
"""
from __future__ import annotations
import logging, time
from typing import Dict, Tuple, Optional
import discord
from discord.ext import commands

log = logging.getLogger(__name__)

TOUCH_TTL_SEC = 10 * 60  # 10 menit

class BanLocalNotify(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._touch_map: Dict[int, Tuple[int, Optional[int], float]] = {}
        self._notified: Dict[int, float] = {}

    # ---------- helpers ----------
    def _touch_set(self, user_id: int, channel_id: int, message_id: Optional[int]) -> None:
        now = time.time()
        if user_id not in self._touch_map:
            self._touch_map[user_id] = (channel_id, message_id, now)
        self._evict_old(now)

    def _touch_get(self, user_id: int) -> Optional[Tuple[int, Optional[int]]]:
        now = time.time()
        self._evict_old(now)
        v = self._touch_map.get(user_id)
        if not v: return None
        ch_id, msg_id, ts = v
        if now - ts > TOUCH_TTL_SEC:
            self._touch_map.pop(user_id, None)
            return None
        return ch_id, msg_id

    def _evict_old(self, now: float) -> None:
        drop = [uid for uid, (_, __, ts) in self._touch_map.items() if now - ts > TOUCH_TTL_SEC]
        for uid in drop:
            self._touch_map.pop(uid, None)

    async def _try_unarchive(self, ch: discord.abc.GuildChannel) -> None:
        try:
            if isinstance(ch, discord.Thread) and ch.archived:
                await ch.edit(archived=False)
        except Exception:
            pass

    async def _fetch_ban_audit(self, guild: discord.Guild, user: discord.User):
        try:
            async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.ban):
                if entry.target.id == user.id:
                    mod_name = str(entry.user) if entry.user else None
                    return mod_name, entry.reason
        except Exception:
            pass
        return None, None

    # ---------- events ----------
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.guild or message.author.bot:
            return
        self._touch_set(message.author.id, message.channel.id, message.id)

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        if user.id in self._notified:
            return
        chmsg = self._touch_get(user.id)
        if not chmsg:
            return
        channel_id, message_id = chmsg
        ch = self.bot.get_channel(channel_id) or await self.bot.fetch_channel(channel_id)
        if not isinstance(ch, (discord.TextChannel, discord.Thread)):
            return

        perms = ch.permissions_for(guild.me)
        if not (perms.send_messages and perms.embed_links):
            return

        await self._try_unarchive(ch)

        mod_name, reason = await self._fetch_ban_audit(guild, user)

        title = "🚫 Pengguna terbanned"
        desc = f"**{user}** (`{user.id}`) telah dibanned."
        if reason: desc += f"\n**Alasan:** {reason}"
        embed = discord.Embed(title=title, description=desc, color=0xE74C3C)
        embed.add_field(name="Channel", value=ch.mention, inline=True)
        if mod_name: embed.add_field(name="Moderator", value=mod_name, inline=True)
        if message_id:
            try:
                jump = f"https://discord.com/channels/{guild.id}/{channel_id}/{message_id}"
                embed.add_field(name="Pesan awal", value=f"[jump]({jump})", inline=False)
            except Exception:
                pass
        embed.set_footer(text="FIRST_TOUCHDOWN_BAN")
        try:
            await ch.send(embed=embed)
            self._notified[user.id] = time.time()
        except Exception as e:
            log.warning("[ban-local-notify] failed to send: %r", e)

async def setup(bot: commands.Bot):
    await bot.add_cog(BanLocalNotify(bot))
