
from __future__ import annotations
import json, re, asyncio
from pathlib import Path
import discord
from discord.ext import commands
from discord import app_commands

CFG_PATH = Path("config/auto_role_anywhere.json")
REASON = "Auto-role via thread/channel activity"

# intervals (no ENV)
THREAD_SWEEP_SECONDS   = 600   # threads
CHANNEL_SWEEP_SECONDS  = 900   # text channels
CHANNEL_BACKFILL_LIMIT = 400
SUBSLEEP_SECONDS       = 0.25

def _casefold(s: str) -> str: return s.casefold()

def _load_cfg() -> dict:
    if CFG_PATH.exists():
        with CFG_PATH.open("r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "thread_name_map": {},
        "channel_id_map": {},
        "channel_name_map": {},
        "category_id_map": {},
        "regex_rules": []
    }

class AutoRoleAnywhere(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.cfg = _load_cfg()
        # tasks will be started on on_ready to avoid .loop dependency (smoke DummyBot has no .loop)
        self._thread_task: asyncio.Task | None = None
        self._channel_task: asyncio.Task | None = None

    def cog_unload(self):
        for t in (self._thread_task, self._channel_task):
            if t and not t.done():
                t.cancel()

    # ---- role resolution ----
    def _resolve_role(self, guild: discord.Guild, spec: int | str) -> discord.Role | None:
        if isinstance(spec, int) or (isinstance(spec, str) and str(spec).isdigit()):
            return guild.get_role(int(spec))
        name = _casefold(str(spec))
        return discord.utils.find(lambda r: _casefold(r.name) == name, guild.roles)

    async def _grant(self, guild: discord.Guild, user_id: int, role_spec: int | str):
        try:
            member = guild.get_member(user_id) or await guild.fetch_member(user_id)
        except discord.HTTPException:
            return
        role = self._resolve_role(guild, role_spec)
        if not role or role in member.roles:
            return
        try:
            await member.add_roles(role, reason=REASON)
        except discord.Forbidden:
            pass

    # ---- matching ----
    def _role_from_text_channel(self, ch: discord.abc.GuildChannel):
        ref = (self.cfg.get("channel_id_map") or {}).get(str(ch.id))
        if ref: return ref.get("role")
        name = _casefold(ch.name)
        for key, v in (self.cfg.get("channel_name_map") or {}).items():
            k = _casefold(key)
            if v.get("exact"):
                if name == k: return v.get("role")
            else:
                if k in name: return v.get("role")
        cat = getattr(ch, "category", None)
        if cat:
            cref = (self.cfg.get("category_id_map") or {}).get(str(cat.id))
            if cref: return cref.get("role")
        for rr in self.cfg.get("regex_rules") or []:
            try:
                if re.search(rr.get("pattern",""), name, re.I): return rr.get("role")
            except re.error:
                continue
        return None

    def _role_from_thread(self, thread: discord.Thread):
        tname = _casefold(thread.name)
        for key, v in (self.cfg.get("thread_name_map") or {}).items():
            if v.get("exact") and _casefold(key) == tname:
                return v.get("role")
        for key, v in (self.cfg.get("thread_name_map") or {}).items():
            if not v.get("exact") and _casefold(key) in tname:
                return v.get("role")
        parent = thread.parent
        if parent:
            parent_role = self._role_from_text_channel(parent)
            if parent_role: return parent_role
        for rr in self.cfg.get("regex_rules") or []:
            try:
                if re.search(rr.get("pattern",""), tname, re.I): return rr.get("role")
            except re.error:
                continue
        return None

    # ---- sweepers (started on_ready) ----
    async def _sweep_thread_members(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try:
                for guild in self.bot.guilds:
                    for th in guild.threads:
                        if getattr(th, "archived", False):
                            continue
                        role_spec = self._role_from_thread(th)
                        if not role_spec:
                            continue
                        try:
                            await th.join()   # requires Manage Threads OR Send Messages in Threads
                        except Exception:
                            pass
                        try:
                            members = []
                            try:
                                members = await th.fetch_members()
                            except TypeError:
                                async for tm in th.fetch_members():
                                    members.append(tm)
                            for tm in members or []:
                                await self._grant(th.guild, tm.id, role_spec)
                        except Exception:
                            pass
                        await asyncio.sleep(SUBSLEEP_SECONDS)
            except asyncio.CancelledError:
                break
            except Exception:
                pass
            await asyncio.sleep(max(60, THREAD_SWEEP_SECONDS))

    async def _sweep_channels_backfill(self):
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try:
                for guild in self.bot.guilds:
                    targets: list[discord.TextChannel] = []
                    for cid in (self.cfg.get("channel_id_map") or {}).keys():
                        ch = guild.get_channel(int(cid))
                        if isinstance(ch, discord.TextChannel):
                            targets.append(ch)
                    for name_key in (self.cfg.get("channel_name_map") or {}).keys():
                        ch = discord.utils.find(lambda c: isinstance(c, discord.TextChannel) and _casefold(c.name)==_casefold(name_key), guild.channels)
                        if ch and ch not in targets:
                            targets.append(ch)
                    for ch in targets:
                        role_spec = self._role_from_text_channel(ch)
                        if not role_spec:
                            continue
                        perms = ch.permissions_for(guild.me)
                        if not (perms.view_channel and perms.read_message_history):
                            continue
                        seen = set()
                        try:
                            async for msg in ch.history(limit=CHANNEL_BACKFILL_LIMIT, oldest_first=False):
                                if msg.author.bot or not msg.guild:
                                    continue
                                uid = msg.author.id
                                if uid in seen:
                                    continue
                                seen.add(uid)
                                await self._grant(guild, uid, role_spec)
                        except Exception:
                            pass
                        await asyncio.sleep(SUBSLEEP_SECONDS)
            except asyncio.CancelledError:
                break
            except Exception:
                pass
            await asyncio.sleep(max(60, CHANNEL_SWEEP_SECONDS))

    # ---- events ----
    @commands.Cog.listener()
    async def on_ready(self):
        # Start background tasks once, without relying on bot.loop
        if (self._thread_task is None) or self._thread_task.done():
            try:
                self._thread_task = asyncio.create_task(self._sweep_thread_members())
            except RuntimeError:
                # no running loop in smoke? skip silently
                self._thread_task = None
        if (self._channel_task is None) or self._channel_task.done():
            try:
                self._channel_task = asyncio.create_task(self._sweep_channels_backfill())
            except RuntimeError:
                self._channel_task = None

        # keep bot joined to relevant threads
        for g in self.bot.guilds:
            for t in g.threads:
                if self._role_from_thread(t):
                    try: await t.join()
                    except Exception: pass

    @commands.Cog.listener()
    async def on_thread_create(self, thread: discord.Thread):
        if self._role_from_thread(thread):
            try: await thread.join()
            except Exception: pass

    @commands.Cog.listener()
    async def on_thread_member_join(self, tm: discord.ThreadMember):
        try:
            thread = self.bot.get_channel(tm.thread_id) or await self.bot.fetch_channel(tm.thread_id)
        except discord.HTTPException:
            return
        if isinstance(thread, discord.Thread):
            role_spec = self._role_from_thread(thread)
            if role_spec:
                await self._grant(thread.guild, tm.id, role_spec)

    @commands.Cog.listener()
    async def on_thread_members_update(self, thread: discord.Thread, added, removed):
        role_spec = self._role_from_thread(thread)
        if not role_spec: return
        for tm in added or []:
            await self._grant(thread.guild, tm.id, role_spec)

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        if msg.author.bot or not msg.guild: return
        ch = msg.channel
        role_spec = None
        if isinstance(ch, discord.Thread):
            role_spec = self._role_from_thread(ch)
        elif isinstance(ch, (discord.TextChannel, discord.VoiceChannel, discord.StageChannel)):
            role_spec = self._role_from_text_channel(ch)
        if role_spec:
            await self._grant(msg.guild, msg.author.id, role_spec)

    # ---- slash cmds ----
    group = app_commands.Group(name="roleauto", description="Auto role controls")

    @group.command(name="reload", description="Reload auto-role config JSON")
    async def reload_cmd(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("Need Manage Server permission.", ephemeral=True)
        self.cfg = _load_cfg()
        await interaction.response.send_message("Auto-role config reloaded ✅", ephemeral=True)

    @group.command(name="dryrun", description="Test which role would match this channel/thread")
    async def dryrun_cmd(self, interaction: discord.Interaction):
        ch = interaction.channel
        role_spec = None
        if isinstance(ch, discord.Thread):
            role_spec = self._role_from_thread(ch)
        elif isinstance(ch, (discord.TextChannel, discord.VoiceChannel, discord.StageChannel)):
            role_spec = self._role_from_text_channel(ch)
        await interaction.response.send_message(f"Match: {role_spec!r}" if role_spec else "No match.", ephemeral=True)

    @group.command(name="backfill", description="Grant role ke author unik dari riwayat channel/thread ini")
    @app_commands.describe(limit="Jumlah pesan yang discan (1–2000, default 500)")
    async def backfill_cmd(self, interaction: discord.Interaction, limit: int = 500):
        if not interaction.user.guild_permissions.manage_guild:
            return await interaction.response.send_message("Need Manage Server permission.", ephemeral=True)

        ch = interaction.channel
        role_spec = None
        if isinstance(ch, discord.Thread):
            role_spec = self._role_from_thread(ch)
        elif isinstance(ch, (discord.TextChannel, discord.VoiceChannel, discord.StageChannel)):
            role_spec = self._role_from_text_channel(ch)

        if not role_spec:
            return await interaction.response.send_message("Channel/thread ini tidak terkonfigurasi untuk autorole.", ephemeral=True)

        perms = ch.permissions_for(ch.guild.me)
        if not (perms.view_channel and getattr(perms, "read_message_history", True)):
            return await interaction.response.send_message("Bot tidak punya izin Read Message History di sini.", ephemeral=True)

        limit = max(1, min(2000, int(limit)))
        await interaction.response.send_message(f"Backfill… scan {limit} pesan terakhir.", ephemeral=True)

        seen = set()
        async for msg in ch.history(limit=limit, oldest_first=False):
            if msg.author.bot or not msg.guild:
                continue
            uid = msg.author.id
            if uid in seen:
                continue
            seen.add(uid)
            await self._grant(msg.guild, uid, role_spec)

        await interaction.followup.send(f"Selesai. User unik diproses: {len(seen)}. Role ditambahkan bila belum punya.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(AutoRoleAnywhere(bot))
    try:
        bot.tree.add_command(AutoRoleAnywhere.group)
    except Exception:
        pass
