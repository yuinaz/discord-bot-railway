import asyncio, logging, traceback, os, datetime as dt
from typing import Optional
import discord
from discord.ext import commands, tasks
from discord import app_commands

# === Config ===
ENV_ID  = "ERRORLOG_CHANNEL_ID"
ENV_NAME= "ERRORLOG_CHANNEL_NAME"   # fallback if ID not set
FALLBACK_NAME = "errorlog-bot"      # default name to search
WIB_TZ = dt.timezone(dt.timedelta(hours=7))  # simple WIB offset

class _DiscordLogHandler(logging.Handler):
    """Logging handler that forwards ERROR/CRITICAL records into an asyncio queue."""
    def __init__(self, queue: asyncio.Queue):
        super().__init__(level=logging.ERROR)
        self.queue = queue

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
        except Exception:
            msg = f"{record.levelname}: {record.getMessage()}"
        # keep it compact, 1900 chars budget (Discord limit 2000 incl. markdown)
        if len(msg) > 1900:
            msg = msg[-1900:]
        try:
            self.queue.put_nowait(("log", msg))
        except asyncio.QueueFull:
            pass

def _format_exception(exc: BaseException) -> str:
    tb = ''.join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    if len(tb) > 1800:
        tb = tb[-1800:]
    now = dt.datetime.now(WIB_TZ).strftime("%Y-%m-%d %H:%M:%S WIB")
    return f"**❌ Unhandled Exception @ {now}**\n```py\n{tb}\n```"

class ErrorLogBridge(commands.Cog):
    """Forward errors to a dedicated channel (#errorlog-bot)."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=200)
        self._handler: Optional[_DiscordLogHandler] = None
        self._channel_id: Optional[int] = None
        self._channel_name: Optional[str] = None
        self._install_handler()
        self.pump.start()

    # ---------- lifecycle ----------
    def cog_unload(self):
        self.pump.cancel()
        if self._handler:
            root = logging.getLogger()
            try:
                root.removeHandler(self._handler)
            except Exception:
                pass
            self._handler = None

    def _install_handler(self):
        # Avoid double install
        root = logging.getLogger()
        for h in root.handlers:
            if isinstance(h, _DiscordLogHandler):
                self._handler = h
                break
        if not self._handler:
            self._handler = _DiscordLogHandler(self._queue)
            fmt = logging.Formatter("[%(levelname)s] %(name)s: %(message)s")
            self._handler.setFormatter(fmt)
            root.addHandler(self._handler)

        # Load env
        cid = (os.getenv(ENV_ID) or "").strip()
        cname = (os.getenv(ENV_NAME) or "").strip() or FALLBACK_NAME
        try:
            self._channel_id = int(cid) if cid.isdigit() else None
        except Exception:
            self._channel_id = None
        self._channel_name = cname or FALLBACK_NAME

    # ---------- channel resolve ----------
    def _resolve_channel(self) -> Optional[discord.TextChannel]:
        # Priority: explicit ID -> name search -> first text channel we can send
        if self._channel_id:
            for g in self.bot.guilds:
                ch = g.get_channel(self._channel_id)
                if isinstance(ch, discord.TextChannel):
                    perms = ch.permissions_for(g.me)
                    if perms.send_messages and perms.embed_links:
                        return ch
        # by name
        name = (self._channel_name or FALLBACK_NAME).lstrip("#").lower()
        for g in self.bot.guilds:
            for ch in g.text_channels:
                if ch.name.lower() == name:
                    perms = ch.permissions_for(g.me)
                    if perms.send_messages:
                        return ch
        # any channel we can send
        for g in self.bot.guilds:
            for ch in g.text_channels:
                perms = ch.permissions_for(g.me)
                if perms.send_messages:
                    return ch
        return None

    # ---------- queue pump ----------
    @tasks.loop(seconds=1.2)
    async def pump(self):
        await self.bot.wait_until_ready()
        ch = self._resolve_channel()
        if not ch:
            return
        sent = 0
        while sent < 3:
            try:
                kind, payload = self._queue.get_nowait()
            except asyncio.QueueEmpty:
                break
            try:
                if kind == "log":
                    await ch.send(payload)
                elif kind == "exc":
                    await ch.send(payload)
            except discord.HTTPException:
                # put back once if failed
                try: self._queue.put_nowait((kind, payload))
                except asyncio.QueueFull: pass
                break
            sent += 1

    @pump.before_loop
    async def _before_pump(self):
        await self.bot.wait_until_ready()

    # ---------- discord events / errors ----------
    async def on_tree_error(self, interaction: Optional[discord.Interaction], error: Exception):
        msg = _format_exception(error)
        try:
            self._queue.put_nowait(("exc", msg))
        except asyncio.QueueFull:
            pass

    @commands.Cog.listener()
    async def on_error(self, event_method: str, *args, **kwargs):
        # Capture generic event errors (Flask style)
        msg = f"**❌ on_error:** `{event_method}`"
        try:
            raise  # Let discord.py build the traceback for us
        except Exception as exc:  # won't run
            pass

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: Exception):
        # Skip common ignore cases (like CommandNotFound for prefix bots)
        if isinstance(error, commands.CommandNotFound):
            return
        msg = _format_exception(error)
        try:
            self._queue.put_nowait(("exc", f"{msg}\n**Command:** `{ctx.command}` by {ctx.author.mention} in {ctx.channel.mention}"))
        except asyncio.QueueFull:
            pass

    # ---------- slash tools ----------
    @app_commands.command(name="set-errorlog", description="Set channel error log (Kosongkan untuk cari otomatis).")
    @app_commands.describe(channel="Channel tujuan error log")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.guild_only()
    async def set_errorlog(self, interaction: discord.Interaction, channel: Optional[discord.TextChannel] = None):
        await interaction.response.defer(ephemeral=True, thinking=True)
        if channel:
            self._channel_id = channel.id
            self._channel_name = channel.name
        else:
            self._channel_id = None  # force resolve by name
        ch = self._resolve_channel()
        if ch:
            await interaction.followup.send(f"✅ Error log diarahkan ke {ch.mention}.", ephemeral=True)
        else:
            await interaction.followup.send("❌ Gagal menemukan channel untuk error log.", ephemeral=True)

    @app_commands.command(name="test-errorlog", description="Kirim pesan test ke channel error log.")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    @app_commands.guild_only()
    async def test_errorlog(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True, thinking=True)
        ch = self._resolve_channel()
        if not ch:
            return await interaction.followup.send("❌ Tidak menemukan channel error log.", ephemeral=True)
        now = dt.datetime.now(WIB_TZ).strftime("%Y-%m-%d %H:%M:%S WIB")
        await ch.send(f"🧪 **Test error log** @ {now} — server: **{interaction.guild.name}**")
        await interaction.followup.send(f"✅ Test terkirim ke {ch.mention}.", ephemeral=True)

async def setup(bot: commands.Bot):
    cog = ErrorLogBridge(bot)
    # hook tree error
    bot.tree.on_error = cog.on_tree_error  # type: ignore[assignment]
    await bot.add_cog(cog)
