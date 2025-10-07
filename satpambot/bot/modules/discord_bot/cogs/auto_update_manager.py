
from __future__ import annotations
import asyncio, json, subprocess, sys, os, time
from typing import List, Dict, Any
try:
    import discord
    from discord import app_commands
    from discord.ext import commands, tasks
except Exception:
    discord = None  # type: ignore
    app_commands = None  # type: ignore
    commands = object  # type: ignore
    tasks = object  # type: ignore

from satpambot.config.runtime import cfg, set_cfg

CONFIG_PATH = cfg('UPDATER_CONFIG') or 'updater_config.yaml'

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
    owner_id = cfg('OWNER_USER_ID')
    if owner_id and str(user.id) == str(owner_id):
        return True
    if cfg('COMMANDS_OWNER_ONLY', True):
        return False
    if hasattr(user,'guild_permissions'):
        perms = user.guild_permissions
        return getattr(perms,'manage_guild',False) or getattr(perms,'administrator',False)
    return False

def _chunk(s: str, n: int):
    for i in range(0, len(s), n):
        yield s[i:i+n]

def _crucial_set() -> set[str]:
    # Crucial packages require owner approval to update
    base = set([x.strip().lower() for x in str(cfg('CRUCIAL_PACKAGES', 'openai,discord.py,numpy,pandas,Pillow')).split(',') if x.strip()])
    return base

def _approved_once() -> set[str]:
    arr = cfg('UPD_APPROVE_ONCE', []) or []
    return set([str(x).lower() for x in arr])

def _push_approved(name: str):
    arr = list(_approved_once())
    arr.append(name.lower())
    set_cfg('UPD_APPROVE_ONCE', arr)
    # Expire marker timestamp (1 hour window)
    set_cfg('UPD_APPROVE_TS', int(time.time()))

class AutoUpdateManager(commands.Cog):  # type: ignore
    def __init__(self, bot: 'commands.Bot'):
        self.bot = bot
        self.cfg_yaml = _read_yaml(CONFIG_PATH)
        days = int((self.cfg_yaml.get('schedule_days') or 4))
        self.interval = max(1, days) * 24 * 3600
        self.auto_apply = False if _is_render_env() else (str(self.cfg_yaml.get('auto_apply_non_critical','true')).lower() in ('1','true','yes','on'))
        self.allow = set((self.cfg_yaml.get('allow_packages') or []))
        self.deny  = set((self.cfg_yaml.get('deny_packages') or []))
        self.dm_owner = cfg('UPDATE_DM_OWNER', True)
        if hasattr(self,'periodic_check'):
            self.periodic_check.change_interval(seconds=self.interval)  # type: ignore
            self.periodic_check.start()  # type: ignore

    def _mk_embed(self, title: str, description: str = '', color: int = 0x2ecc71, fields: List[tuple] | None = None):
        if discord is None: return None
        em = discord.Embed(title=title, description=description or discord.Embed.Empty, color=color)
        if fields:
            for name, value, inline in fields:
                if not value: value = '-'
                for chunk in _chunk(str(value), 1024):
                    em.add_field(name=name, value=chunk, inline=inline)
                    name = '…'
        return em

    async def _notify_owner_embed(self, embed):
        if not self.dm_owner or discord is None or embed is None:
            return
        owner_id = cfg('OWNER_USER_ID')
        if not owner_id: return
        try:
            user = self.bot.get_user(int(owner_id)) or await self.bot.fetch_user(int(owner_id))
            if user: await user.send(embed=embed)
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

    def _filter_update_set(self, outdated: List[Dict[str, Any]]) -> List[str]:
        crucial = _crucial_set()
        approved = _approved_once()
        # expire approval after 1 hour
        ts = int(cfg('UPD_APPROVE_TS', 0) or 0)
        if ts and (time.time() - ts) > 3600:
            set_cfg('UPD_APPROVE_ONCE', []); set_cfg('UPD_APPROVE_TS', 0)
            approved = set()

        pkgs = []
        for i in outdated:
            name = i['name']
            lname = name.lower()
            if lname in {p.lower() for p in self.deny}: continue
            if self.allow and lname not in {p.lower() for p in self.allow}: continue
            # block crucial unless approved
            if lname in crucial and lname not in approved:
                continue
            # always constrain openai to v1 major
            if lname == 'openai':
                pkgs.append('openai>=1,<2')
            else:
                pkgs.append(f"{name}=={i['latest_version']}")
        return pkgs

    @commands.Cog.listener()
    async def on_message(self, message: 'discord.Message'):
        if discord is None or message.author.bot: return
        if not isinstance(message.channel, (discord.DMChannel, discord.GroupChannel)): return
        if not is_owner(message.author): return
        content = message.content.strip().lower()
        if content in ('check update', 'check updates', 'update check'):
            outdated = pip_list_outdated()
            lines = summarize_outdated(outdated, limit=20)
            embed = self._mk_embed('Manual — Update Check', '', 0x3498db, fields=[('Outdated', '\n'.join(lines) or '-', False), ('Total', str(len(outdated)), True)])
            await message.channel.send(embed=embed)
        elif content.startswith('approve update '):
            pkg = content.split('approve update ',1)[1].strip()
            if pkg:
                _push_approved(pkg)
                await message.channel.send(embed=self._mk_embed('Approval', f'Approved once: `{pkg}` (valid 1 hour)', 0x2ecc71))
        elif content in ('check error','check errors','diagnose','diag'):
            ok, out = run_smoke_all()
            color = 0x2ecc71 if ok else 0xe74c3c
            tail = (out or '')[-1800:]
            embed = self._mk_embed('Manual — Diagnostics', 'All green' if ok else 'Issues found', color, [('Log tail', f'```\n{tail}\n```', False)])
            await message.channel.send(embed=embed)
        elif content in ('update apply','apply update'):
            outdated = pip_list_outdated()
            pkgs = self._filter_update_set(outdated)
            if _is_render_env():
                embed = self._mk_embed('Manual — Update Apply', f'Render environment: report-only. Candidates:\n- ' + '\n- '.join(pkgs or ['(none)']), 0x95a5a6)
                await message.channel.send(embed=embed)
            else:
                if not pkgs:
                    await message.channel.send(embed=self._mk_embed('Manual — Update Apply', 'No non-critical/approved updates to apply.', 0x95a5a6))
                else:
                    pip_freeze('requirements.lock.local')
                    ok = pip_install_pkgs(pkgs)
                    diag_ok, _ = run_smoke_all()
                    if ok and diag_ok:
                        await message.channel.send(embed=self._mk_embed('Manual — Update Apply', 'Success', 0x2ecc71, [('Applied', '\n'.join(pkgs), False)]))
                    else:
                        subprocess.call([sys.executable,'-m','pip','install','--no-cache-dir','-r','requirements.lock.local'])
                        await message.channel.send(embed=self._mk_embed('Manual — Update Apply', 'Failed — rolled back.', 0xe74c3c))

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

        @app_commands.command(name='approve_update', description='(Owner) Approve update untuk 1 package (valid 1 jam)')
        async def approve_update(self, interaction: 'discord.Interaction', package_name: str):
            if not await self._owner_gate(interaction): return
            _push_approved(package_name)
            await interaction.response.send_message(embed=self._mk_embed('Approval', f'Approved once: `{package_name}` (valid 1 hour)', 0x2ecc71), ephemeral=True)

        @app_commands.command(name='update_apply', description='(Owner) Apply updates (non-critical & approved)')
        async def update_apply(self, interaction: 'discord.Interaction'):
            if not await self._owner_gate(interaction): return
            await interaction.response.defer(ephemeral=True)
            outdated = pip_list_outdated()
            pkgs = self._filter_update_set(outdated)
            if _is_render_env():
                await interaction.followup.send(embed=self._mk_embed('Slash — Update Apply', 'Render: report-only', 0x95a5a6), ephemeral=True); return
            if not pkgs:
                await interaction.followup.send(embed=self._mk_embed('Slash — Update Apply', 'No non-critical/approved updates.', 0x95a5a6), ephemeral=True); return
            pip_freeze('requirements.lock.local')
            ok = pip_install_pkgs(pkgs); diag_ok, _ = run_smoke_all()
            if ok and diag_ok:
                await interaction.followup.send(embed=self._mk_embed('Slash — Update Apply', 'Success', 0x2ecc71, [('Applied', '\n'.join(pkgs), False)]), ephemeral=True)
            else:
                subprocess.call([sys.executable,'-m','pip','install','--no-cache-dir','-r','requirements.lock.local'])
                await interaction.followup.send(embed=self._mk_embed('Slash — Update Apply', 'Failed — rolled back.', 0xe74c3c), ephemeral=True)

async def setup(bot):
    if discord is None or commands is object:
        return
    await bot.add_cog(AutoUpdateManager(bot))
