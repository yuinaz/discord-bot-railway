from __future__ import annotations

from discord.ext import commands

# satpambot/bot/modules/discord_bot/cogs/ban_local_notify.py
import logging, time, inspect, importlib
from typing import Dict, Tuple, Optional, Callable, Any
import discord

log = logging.getLogger(__name__)
TOUCH_TTL_SEC = 10 * 60
NAME_KEYWORDS = ("ban", "tb", "test", "simul", "embed")
PREFERRED_METHODS = ("build_ban_embed","make_ban_embed","create_ban_embed","ban_embed","make_embed","tb_embed","testban_embed")
PREFERRED_COGS = ("ModerationTest","BanAutoEmbed","BanLogger","ModPolicy","ModerationExtras")
class BanLocalNotify(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._touch_map: Dict[int, Tuple[int, Optional[int], float]] = {}
        self._notified: Dict[int, float] = {}
    def _touch_set(self, user_id: int, channel_id: int, message_id: Optional[int]) -> None:
        now = time.time()
        if user_id not in self._touch_map:
            self._touch_map[user_id] = (channel_id, message_id, now)
        self._evict_old(now)
    def _touch_get(self, user_id: int) -> Optional[Tuple[int, Optional[int]]]:
        now = time.time(); self._evict_old(now)
        v = self._touch_map.get(user_id)
        if not v: return None
        ch_id, msg_id, ts = v
        if now - ts > TOUCH_TTL_SEC:
            self._touch_map.pop(user_id, None); return None
        return ch_id, msg_id
    def _evict_old(self, now: float) -> None:
        drop = [uid for uid, (_, __, ts) in self._touch_map.items() if now - ts > TOUCH_TTL_SEC]
        for uid in drop: self._touch_map.pop(uid, None)
    async def _try_unarchive(self, ch: discord.abc.GuildChannel) -> None:
        try:
            if isinstance(ch, discord.Thread) and ch.archived:
                await ch.edit(archived=False)
        except Exception: pass
    async def _fetch_ban_audit(self, guild: discord.Guild, user: discord.User):
        try:
            async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.ban):
                if entry.target.id == user.id:
                    mod_name = str(entry.user) if entry.user else None
                    return mod_name, entry.reason
        except Exception: pass
        return None, None
    async def _maybe_call(self, fn: Callable[..., Any], **ctx):
        try:
            sig = inspect.signature(fn)
            kwargs = {}
            for name, p in sig.parameters.items():
                low = name.lower()
                if low in ("guild","g"): kwargs[name] = ctx.get("guild")
                elif low in ("user","member","target"): kwargs[name] = ctx.get("user")
                elif low in ("reason","alasan"): kwargs[name] = ctx.get("reason")
                elif low in ("moderator","mod","by","actor"): kwargs[name] = ctx.get("moderator")
                elif low in ("channel","ch"): kwargs[name] = ctx.get("channel")
                elif low in ("message_id","msg_id"): kwargs[name] = ctx.get("message_id")
                elif low in ("jump_url","jump","url"): kwargs[name] = ctx.get("jump_url")
                elif p.default is inspect._empty: 
                    return None
            res = fn(**kwargs)
            if inspect.isawaitable(res): res = await res
            return res
        except Exception:
            return None
    async def _probe_embed_from_cogs(self, guild, user, reason, moderator, channel, message_id) -> Optional[discord.Embed]:
        jump_url = f"https://discord.com/channels/{guild.id}/{channel.id}/{message_id}" if message_id else None
        for cname in PREFERRED_COGS:
            cog = self.bot.get_cog(cname)
            if not cog: continue
            for m in PREFERRED_METHODS:
                fn = getattr(cog, m, None)
                if callable(fn):
                    emb = await self._maybe_call(fn, guild=guild, user=user, reason=reason, moderator=moderator, channel=channel, message_id=message_id, jump_url=jump_url)
                    if isinstance(emb, discord.Embed): return emb
            for name, fn in inspect.getmembers(cog, predicate=callable):
                low = name.lower()
                if any(k in low for k in NAME_KEYWORDS):
                    emb = await self._maybe_call(fn, guild=guild, user=user, reason=reason, moderator=moderator, channel=channel, message_id=message_id, jump_url=jump_url)
                    if isinstance(emb, discord.Embed): return emb
        for modname in (
            "satpambot.bot.modules.discord_bot.cogs.moderation_test",
            "satpambot.bot.modules.discord_bot.cogs.ban_auto_embed",
            "satpambot.bot.modules.discord_bot.cogs.ban_logger",
        ):
            try:
                mod = importlib.import_module(modname)
            except Exception:
                continue
            for name, fn in inspect.getmembers(mod, predicate=callable):
                low = name.lower()
                if any(k in low for k in NAME_KEYWORDS):
                    emb = await self._maybe_call(fn, guild=guild, user=user, reason=reason, moderator=moderator, channel=channel, message_id=message_id, jump_url=jump_url)
                    if isinstance(emb, discord.Embed): return emb
        return None
    def _fallback_embed(self, guild, user, reason, moderator, channel, message_id) -> discord.Embed:
        title = "🚫 Pengguna terbanned"
        desc = f"**{user}** (`{user.id}`) telah dibanned."
        if reason: desc += f"\n**Alasan:** {reason}"
        emb = discord.Embed(title=title, description=desc, color=0xE74C3C)
        emb.add_field(name="Channel", value=channel.mention, inline=True)
        if moderator: emb.add_field(name="Moderator", value=moderator, inline=True)
        if message_id:
            try:
                jump = f"https://discord.com/channels/{guild.id}/{channel.id}/{message_id}"
                emb.add_field(name="Pesan awal", value=f"[jump]({jump})", inline=False)
            except Exception: pass
        emb.set_footer(text="FIRST_TOUCHDOWN_BAN")
        return emb
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # --- PublicChatGate pre-send guard (auto-injected) ---
        gate = None
        try:
            gate = self.bot.get_cog("PublicChatGate")
        except Exception:
            pass
        try:
            if message.guild and gate and hasattr(gate, "should_allow_public_reply") and not gate.should_allow_public_reply(message):
                return
        except Exception:
            pass
        # --- end guard ---

        # THREAD/FORUM EXEMPTION — auto-inserted
        ch = getattr(message, "channel", None)
        if ch is not None:
            try:
                import discord
                # Exempt true Thread objects
                if isinstance(ch, getattr(discord, "Thread", tuple())):
                    return
                # Exempt thread-like channel types (public/private/news threads)
                ctype = getattr(ch, "type", None)
                if ctype in {
                    getattr(discord.ChannelType, "public_thread", None),
                    getattr(discord.ChannelType, "private_thread", None),
                    getattr(discord.ChannelType, "news_thread", None),
                }:
                    return
            except Exception:
                # If discord import/type checks fail, do not block normal flow
                pass
        if not message.guild or message.author.bot: return
        self._touch_set(message.author.id, message.channel.id, message.id)
    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        if user.id in self._notified: return
        chmsg = self._touch_get(user.id)
        if not chmsg: return
        channel_id, message_id = chmsg
        ch = self.bot.get_channel(channel_id) or await self.bot.fetch_channel(channel_id)
        if not isinstance(ch, (discord.TextChannel, discord.Thread)): return
        perms = ch.permissions_for(guild.me)
        if not (perms.send_messages and perms.embed_links): return
        await self._try_unarchive(ch)
        mod_name, reason = await self._fetch_ban_audit(guild, user)
        emb = await self._probe_embed_from_cogs(guild, user, reason, mod_name, ch, message_id)
        if not isinstance(emb, discord.Embed):
            emb = self._fallback_embed(guild, user, reason, mod_name, ch, message_id)
        try:
            await ch.send(embed=emb, delete_after=3600); self._notified[user.id] = time.time()
        except Exception as e:
            log.warning("[ban-local-notify] failed to send: %r", e)
async def setup(bot: commands.Bot): await bot.add_cog(BanLocalNotify(bot))