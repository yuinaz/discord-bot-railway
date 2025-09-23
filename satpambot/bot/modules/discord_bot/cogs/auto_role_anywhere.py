
from __future__ import annotations
import json, re
from pathlib import Path
import discord
from discord.ext import commands
from discord import app_commands

CFG_PATH = Path("config/auto_role_anywhere.json")
REASON = "Auto-role via thread/channel activity"

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

    def _resolve_role(self, guild: discord.Guild, spec: int | str) -> discord.Role | None:
        if isinstance(spec, int) or (isinstance(spec, str) and spec.isdigit()):
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
        if thread.parent:
            parent_role = self._role_from_text_channel(thread.parent)
            if parent_role: return parent_role
        for rr in self.cfg.get("regex_rules") or []:
            try:
                if re.search(rr.get("pattern",""), tname, re.I): return rr.get("role")
            except re.error:
                continue
        return None

    @commands.Cog.listener()
    async def on_ready(self):
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

async def setup(bot: commands.Bot):
    await bot.add_cog(AutoRoleAnywhere(bot))
    try:
        bot.tree.add_command(AutoRoleAnywhere.group)
    except Exception:
        pass
