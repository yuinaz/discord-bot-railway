
from __future__ import annotations
import os, contextlib
from datetime import datetime, timezone
from typing import Dict, Optional
import discord
from discord.ext import commands, tasks

MARKER = "sticky-status:v1"

def _env_bool(name: str, default: str="1") -> bool:
    return os.getenv(name, default) not in ("0", "false", "False", "", None)

CANDIDATE_CHANNEL_NAMES = ["log-botphising","log-botphishing","bot-logs","bot-log","logs","status","bot-status","general","umum"]

class _GuildState:
    __slots__ = ("channel_id", "message_id")
    def __init__(self):
        self.channel_id: Optional[int] = None
        self.message_id: Optional[int] = None

class StatusStickyAuto(commands.Cog):
    """Auto sticky status: default pinned + update 15 menit, tanpa ENV wajib."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.enabled = _env_bool("STICKY_ENABLED", "1")
        self.interval = max(60, int(os.getenv("STICKY_INTERVAL_SEC", "900")))  # 15 menit
        self.pin = _env_bool("STICKY_PIN", "1")  # default pinned
        self.state: Dict[int, _GuildState] = {}
        self._started = False

    @staticmethod
    def _can_send(ch: discord.TextChannel) -> bool:
        me = ch.guild.me
        if not me: return False
        p = ch.permissions_for(me)
        return p.send_messages and p.embed_links

    async def _pick_channel(self, g: discord.Guild) -> Optional[discord.TextChannel]:
        st = self.state.setdefault(g.id, _GuildState())
        if st.channel_id:
            ch = g.get_channel(st.channel_id)
            if isinstance(ch, discord.TextChannel) and self._can_send(ch):
                return ch
        raw = os.getenv("LOG_CHANNEL_ID")
        if raw and raw.isdigit():
            ch = g.get_channel(int(raw))
            if isinstance(ch, discord.TextChannel) and self._can_send(ch):
                st.channel_id = ch.id; return ch
        for name in CANDIDATE_CHANNEL_NAMES:
            ch = discord.utils.get(g.text_channels, name=name)
            if isinstance(ch, discord.TextChannel) and self._can_send(ch):
                st.channel_id = ch.id; return ch
        for ch in g.text_channels:
            if self._can_send(ch):
                st.channel_id = ch.id; return ch
        return None

    @staticmethod
    def _embed() -> discord.Embed:
        now = datetime.now(timezone.utc)
        epoch = int(now.timestamp())
        emb = discord.Embed(
            title="SatpamBot Status",
            description="✅ **SatpamBot online dan siap berjaga.**",
            colour=discord.Colour.from_str(os.getenv("STICKY_COLOR", "#22c55e"))
        )
        emb.add_field(name="Terakhir diperbarui", value=f"<t:{epoch}:f>", inline=False)
        emb.set_footer(text=MARKER)
        return emb

    async def _find_existing(self, ch: discord.TextChannel) -> Optional[discord.Message]:
        try:
            async for msg in ch.history(limit=30):
                if msg.author == self.bot.user and msg.embeds:
                    emb = msg.embeds[0]
                    if (emb.footer and emb.footer.text == MARKER) or ("SatpamBot Status" in (emb.title or "")):
                        return msg
        except Exception:
            return None
        return None

    async def _upsert(self, g: discord.Guild):
        ch = await self._pick_channel(g)
        if not isinstance(ch, discord.TextChannel):
            return
        st = self.state.setdefault(g.id, _GuildState())
        emb = self._embed()
        msg = None
        if st.message_id:
            try:
                msg = await ch.fetch_message(st.message_id)
            except Exception:
                msg = None
            if msg and (not msg.embeds or (msg.author != self.bot.user)):
                msg = None
        if not msg:
            msg = await self._find_existing(ch)
        if msg:
            with contextlib.suppress(Exception):
                await msg.edit(embed=emb)
            st.message_id = msg.id
            if self.pin:
                with contextlib.suppress(Exception):
                    await msg.pin(reason="SatpamBot sticky status")
            return
        try:
            msg = await ch.send(embed=emb)
            st.message_id = msg.id
            if self.pin:
                with contextlib.suppress(Exception):
                    await msg.pin(reason="SatpamBot sticky status")
        except Exception:
            pass

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.enabled or self._started:
            return
        self._started = True
        for g in self.bot.guilds:
            try:
                await self._upsert(g)
            except Exception:
                pass
        self.loop.change_interval(seconds=self.interval)
        self.loop.start()

    @tasks.loop(seconds=900)
    async def loop(self):
        for g in list(self.bot.guilds):
            try:
                await self._upsert(g)
            except Exception:
                pass

    @loop.before_loop
    async def before(self):
        await self.bot.wait_until_ready()

    @commands.command(name="status-refresh")
    @commands.has_permissions(manage_guild=True)
    async def status_refresh(self, ctx: commands.Context):
        await self._upsert(ctx.guild)
        await ctx.reply("✅ Sticky status diperbarui.", mention_author=False)

async def setup(bot: commands.Bot):
    await bot.add_cog(StatusStickyAuto(bot))
