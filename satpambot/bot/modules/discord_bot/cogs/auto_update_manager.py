from __future__ import annotations
import asyncio, json, os, sys, subprocess
from typing import List, Dict, Any, Iterable
try:
    import discord
    from discord import app_commands
    from discord.ext import commands, tasks
except Exception:
    discord = None  # type: ignore
    app_commands = None  # type: ignore
    commands = object  # type: ignore
    tasks = object  # type: ignore

CONFIG_PATH = os.environ.get('UPDATER_CONFIG', 'updater_config.yaml')

def _read_yaml(path: str) -> Dict[str, Any]:
    try:
        import yaml
        with open(path, 'r', encoding='utf-8') as f:
            return (yaml.safe_load(f) or {})
    except Exception:
        return {}

def _is_render_env() -> bool:
    return any(os.environ.get(k) for k in ('RENDER','RENDER_SERVICE_ID','RENDER_EXTERNAL_URL'))

def pip_list_outdated() -> List[Dict[str, Any]]:
    try:
        out = subprocess.check_output([sys.executable,'-m','pip','list','--outdated','--format=json'], text=True)
        return json.loads(out)
    except Exception:
        return []

def pip_freeze(path: str):
    try:
        out = subprocess.check_output([sys.executable,'-m','pip','freeze'], text=True)
        open(path,'w',encoding='utf-8').write(out)
    except Exception:
        pass

def pip_install_pkgs(pkgs: List[str]) -> bool:
    if not pkgs: return True
    try:
        subprocess.check_call([sys.executable,'-m','pip','install','--no-cache-dir',*pkgs])
        return True
    except subprocess.CalledProcessError:
        return False

def run_smoke_all() -> (bool, str):
    cmds = [
        [sys.executable, 'scripts/smoketest_all.py'],
        [sys.executable, 'scripts/smoketest_render.py'],
        [sys.executable, 'scripts/smoke_cogs.py'],
    ]
    last = ''
    for cmd in cmds:
        try:
            out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True)
            return True, out
        except Exception as e:
            last = getattr(e, 'output', str(e)) or str(e)
    return False, last

def summarize_outdated(outdated: List[Dict[str, Any]], limit: int = 10) -> List[str]:
    lines = []
    for i in outdated[:limit]:
        name = i.get('name','?'); cur = i.get('version','?'); new = i.get('latest_version','?')
        lines.append(f"{name}: {cur} → {new}")
    return lines

def is_owner(user: 'discord.abc.User') -> bool:
    owner_id = os.environ.get('OWNER_USER_ID')
    if owner_id and str(user.id) == str(owner_id):
        return True
    if os.environ.get('COMMANDS_OWNER_ONLY','1') in ('1','true','on','yes'):
        return False
    if hasattr(user,'guild_permissions'):
        perms = user.guild_permissions
        return getattr(perms,'manage_guild',False) or getattr(perms,'administrator',False)
    return False

def _chunk(s: str, n: int) -> Iterable[str]:
    for i in range(0, len(s), n):
        yield s[i:i+n]

class AutoUpdateManager(commands.Cog):  # type: ignore
    def __init__(self, bot: 'commands.Bot'):
        self.bot = bot
        self.cfg = _read_yaml(CONFIG_PATH)
        days = int((self.cfg.get('schedule_days') or 4))
        self.interval = max(1, days) * 24 * 3600
        self.auto_apply = False if _is_render_env() else (str(self.cfg.get('auto_apply_non_critical','true')).lower() in ('1','true','yes','on'))
        self.allow = set((self.cfg.get('allow_packages') or []))
        self.deny  = set((self.cfg.get('deny_packages') or []))
        self.dm_owner = os.environ.get('UPDATE_DM_OWNER','1') not in ('0','false','off','no')
        if hasattr(self,'periodic_check'):
            self.periodic_check.change_interval(seconds=self.interval)  # type: ignore
            self.periodic_check.start()  # type: ignore

    def _mk_embed(self, title: str, description: str = '', color: int = 0x2ecc71, fields: List[tuple] | None = None):
        if discord is None:
            return None
        em = discord.Embed(title=title, description=description or discord.Embed.Empty, color=color)
        if fields:
            for name, value, inline in fields:
                if not value:
                    value = '-'
                for chunk in _chunk(str(value), 1024):
                    em.add_field(name=name, value=chunk, inline=inline)
                    name = '…'
        return em

    async def _notify_owner_embed(self, embed):
        if not self.dm_owner or discord is None or embed is None:
            return
        owner_id = os.environ.get('OWNER_USER_ID')
        if not owner_id:
            return
        try:
            user = self.bot.get_user(int(owner_id)) or await self.bot.fetch_user(int(owner_id))
            if user:
                await user.send(embed=embed)
        except Exception:
            pass

    async def cog_load(self):
        await asyncio.sleep(3)
        ok, out = run_smoke_all()
        color = 0x2ecc71 if ok else 0xe74c3c
        desc = 'All green' if ok else 'Issues detected'
        tail = (out or '')[-1800:]
        embed = self._mk_embed('Startup Check', desc, color, fields=[('Log tail', f'```\n{tail}\n```', False)])
        await self._notify_owner_embed(embed)

    @tasks.loop(seconds=4*24*3600)
    async def periodic_check(self):
        outdated = pip_list_outdated()
        lines = summarize_outdated(outdated, limit=10)
        fields = [('Outdated (top 10)', '\n'.join(lines) or '-', False), ('Total', str(len(outdated)), True)]
        embed = self._mk_embed('AutoUpdate — Report', 'Render: report-only' if _is_render_env() else 'MiniPC: auto-apply non-critical', 0xf5b041, fields)
        await self._notify_owner_embed(embed)

    @commands.Cog.listener()
    async def on_message(self, message: 'discord.Message'):
        if discord is None or message.author.bot:
            return
        if not isinstance(message.channel, (discord.DMChannel, discord.GroupChannel)):
            return
        if not is_owner(message.author):
            return
        content = message.content.strip().lower()
        if content in ('check update', 'check updates', 'update check'):
            outdated = pip_list_outdated()
            lines = summarize_outdated(outdated, limit=20)
            embed = self._mk_embed('Manual — Update Check', '', 0x3498db, fields=[('Outdated', '\n'.join(lines) or '-', False), ('Total', str(len(outdated)), True)])
            await message.channel.send(embed=embed)
        elif content in ('check error','check errors','diagnose','diag'):
            ok, out = run_smoke_all()
            color = 0x2ecc71 if ok else 0xe74c3c
            tail = (out or '')[-1800:]
            embed = self._mk_embed('Manual — Diagnostics', 'All green' if ok else 'Issues found', color, [('Log tail', f'```\n{tail}\n```', False)])
            await message.channel.send(embed=embed)
        elif content in ('update apply','apply update'):
            if _is_render_env():
                embed = self._mk_embed('Manual — Update Apply', 'Render environment: use redeploy/build.', 0x95a5a6)
                await message.channel.send(embed=embed)
            else:
                outdated = pip_list_outdated()
                pkgs = []
                for i in outdated:
                    name = i['name'].lower()
                    if name in {p.lower() for p in self.deny}: continue
                    if self.allow and name not in {p.lower() for p in self.allow}: continue
                    if name == 'openai': pkgs.append('openai>=1,<2')
                    else: pkgs.append(f"{i['name']}=={i['latest_version']}")
                if not pkgs:
                    await message.channel.send(embed=self._mk_embed('Manual — Update Apply', 'No non-critical updates to apply.', 0x95a5a6))
                else:
                    pip_freeze('requirements.lock.local')
                    ok = pip_install_pkgs(pkgs)
                    diag_ok, diag_out = run_smoke_all()
                    if ok and diag_ok:
                        embed = self._mk_embed('Manual — Update Apply', 'Success', 0x2ecc71, [('Applied', '\n'.join(pkgs), False)])
                        await message.channel.send(embed=embed)
                    else:
                        subprocess.call([sys.executable,'-m','pip','install','--no-cache-dir','-r','requirements.lock.local'])
                        embed = self._mk_embed('Manual — Update Apply', 'Failed — rolled back.', 0xe74c3c)
                        await message.channel.send(embed=embed)

    if app_commands:
        async def _owner_gate(self, interaction: 'discord.Interaction') -> bool:
            if not is_owner(interaction.user):
                await interaction.response.send_message('Owner only.', ephemeral=True)
                return False
            return True

        @app_commands.command(name='update_check', description='(Owner) Cek paket Python yang outdated.')
        async def update_check(self, interaction: 'discord.Interaction'):
            if not await self._owner_gate(interaction): return
            outdated = pip_list_outdated()
            lines = summarize_outdated(outdated, limit=20)
            embed = self._mk_embed('Slash — Update Check', '', 0x3498db, [('Outdated', '\n'.join(lines) or '-', False), ('Total', str(len(outdated)), True)])
            await interaction.response.send_message(embed=embed, ephemeral=True)

        @app_commands.command(name='update_apply', description='(Owner) Update paket non-kritis (MiniPC).')
        async def update_apply(self, interaction: 'discord.Interaction'):
            if not await self._owner_gate(interaction): return
            await interaction.response.defer(ephemeral=True)
            if _is_render_env():
                await interaction.followup.send(embed=self._mk_embed('Slash — Update Apply', 'Render: use redeploy/build.', 0x95a5a6), ephemeral=True); return
            outdated = pip_list_outdated()
            pkgs = []
            for i in outdated:
                name = i['name'].lower()
                if name in {p.lower() for p in self.deny}: continue
                if self.allow and name not in {p.lower() for p in self.allow}: continue
                if name == 'openai': pkgs.append('openai>=1,<2')
                else: pkgs.append(f"{i['name']}=={i['latest_version']}")
            if not pkgs:
                await interaction.followup.send(embed=self._mk_embed('Slash — Update Apply', 'No non-critical updates.', 0x95a5a6), ephemeral=True); return
            pip_freeze('requirements.lock.local')
            ok = pip_install_pkgs(pkgs)
            diag_ok, diag_out = run_smoke_all()
            if ok and diag_ok:
                await interaction.followup.send(embed=self._mk_embed('Slash — Update Apply', 'Success', 0x2ecc71, [('Applied', '\n'.join(pkgs), False)]), ephemeral=True)
            else:
                subprocess.call([sys.executable,'-m','pip','install','--no-cache-dir','-r','requirements.lock.local'])
                await interaction.followup.send(embed=self._mk_embed('Slash — Update Apply', 'Failed — rolled back.', 0xe74c3c), ephemeral=True)

async def setup(bot):
    if discord is None or commands is object:
        return
    await bot.add_cog(AutoUpdateManager(bot))
