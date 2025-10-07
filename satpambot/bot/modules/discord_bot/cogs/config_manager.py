
from __future__ import annotations
import json
from typing import Any
import discord
from discord.ext import commands
from discord import app_commands
from satpambot.config.runtime import cfg, set_cfg, all_cfg
from satpambot.config.env_importer import parse_dotenv, import_env_map, file_sha256

def _is_owner(user: 'discord.abc.User') -> bool:
    owner = cfg('OWNER_USER_ID')
    return owner is not None and str(user.id) == str(owner)

class ConfigManager(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if not isinstance(message.channel, (discord.DMChannel, discord.GroupChannel)):
            return
        content = message.content.strip()
        low = content.lower()
        owner = cfg('OWNER_USER_ID')
        if owner is None and low == 'owner claim':
            set_cfg('OWNER_USER_ID', str(message.author.id))
            em = discord.Embed(title='Owner', description='Owner claimed for this bot.', color=0x2ecc71)
            await message.channel.send(embed=em)
            return
        if not _is_owner(message.author):
            return
        if low == 'config show':
            data = all_cfg()
            if 'OWNER_USER_ID' in data:
                data['OWNER_USER_ID'] = str(data['OWNER_USER_ID']) if data['OWNER_USER_ID'] else None
            text = json.dumps(data, indent=2, ensure_ascii=False)[:3900]
            em = discord.Embed(title='Config', description=f'```json\n{text}\n```', color=0x3498db)
            await message.channel.send(embed=em)
        elif low.startswith('config set '):
            try:
                _, _, body = content.partition('config set ')
                key, _, val = body.strip().partition(' ')
                if not key:
                    raise ValueError('bad args')
                set_cfg(key, val)
                await message.channel.send(embed=discord.Embed(title='Config', description=f'Set **{key}** = `{val}` (persisted).', color=0x2ecc71))
            except Exception as e:
                await message.channel.send(f'Format: `config set <KEY> <VALUE>` — {e}')
        elif low in ('import env','import env now'):
            path = cfg('IMPORTED_ENV_FILE', 'SatpamBot.env') or 'SatpamBot.env'
            data = parse_dotenv(path)
            if not data:
                await message.channel.send(embed=discord.Embed(title='ENV Import', description=f'File `{path}` not found / empty.', color=0xe74c3c)); return
            c_cfg, c_sec, skipped, cfg_keys, sec_keys = import_env_map(data)
            sha = file_sha256(path)
            set_cfg('IMPORTED_ENV_SHA_SATPAMBOT', sha)
            set_cfg('IMPORTED_ENV_FILE', path)
            set_cfg('IMPORTED_ENV_LAST_CFG', int(c_cfg))
            set_cfg('IMPORTED_ENV_LAST_SEC', int(c_sec))
            set_cfg('IMPORTED_ENV_LAST_CFG_KEYS', cfg_keys[:40])
            set_cfg('IMPORTED_ENV_LAST_SEC_KEYS', sec_keys[:40])
            set_cfg('IMPORTED_ENV_NOTIFY', True)
            await message.channel.send(embed=discord.Embed(
                title='ENV Import',
                description=f"Imported from `{path}`: cfg={c_cfg}, secrets={c_sec}. Report will be DM\'d.",
                color=0x3498db
            ))

    if app_commands:
        @app_commands.command(name='config_show', description='(Owner) Tampilkan konfigurasi bot')
        async def config_show(self, interaction: 'discord.Interaction'):
            if not _is_owner(interaction.user):
                await interaction.response.send_message('Owner only.', ephemeral=True); return
            data = all_cfg()
            text = json.dumps(data, indent=2, ensure_ascii=False)[:3900]
            await interaction.response.send_message(embed=discord.Embed(title='Config', description=f'```json\n{text}\n```', color=0x3498db), ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(ConfigManager(bot))
