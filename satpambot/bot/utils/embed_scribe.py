
import json, os
from typing import Optional, Dict, Any, Tuple
import discord
from satpambot.config.compat_conf import get as cfg

DEFAULT_STATE_FILE = cfg("EMBED_SCRIBE_STATE", "data/state/embed_scribe.json", str)

def _ensure_parent(path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)

def _load_state(path: str) -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except Exception:
        return {}

def _save_state(path: str, data: Dict[str, Any]):
    _ensure_parent(path)
    tmppath = path + ".tmp"
    with open(tmppath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmppath, path)

class EmbedScribe:
    def __init__(self, bot, state_file: str = DEFAULT_STATE_FILE):
        self.bot = bot
        self.state_file = state_file
        self._state = _load_state(state_file)

    def _get_keypath(self, guild_id: int, channel_id: int, key: str):
        g = self._state.setdefault(str(guild_id), {})
        c = g.setdefault(str(channel_id), {})
        return c, key

    def remember(self, guild_id: int, channel_id: int, key: str, message_id: int):
        c, k = self._get_keypath(guild_id, channel_id, key)
        c[k] = int(message_id)
        _save_state(self.state_file, self._state)

    def recall(self, guild_id: int, channel_id: int, key: str) -> Optional[int]:
        c, k = self._get_keypath(guild_id, channel_id, key)
        mid = c.get(k)
        return int(mid) if mid is not None else None

    async def _search_existing(self, channel: discord.abc.Messageable, key: str) -> Optional[int]:
        try:
            pins = await channel.pins()
            for m in pins:
                if m.author.id == self.bot.user.id and m.embeds:
                    for e in m.embeds:
                        if (e.footer and e.footer.text and f"key:{key}" in e.footer.text):
                            return m.id
        except Exception:
            pass
        try:
            async for m in channel.history(limit=200):
                if m.author.id == self.bot.user.id and m.embeds:
                    for e in m.embeds:
                        if (e.footer and e.footer.text and f"key:{key}" in e.footer.text):
                            return m.id
        except Exception:
            pass
        return None

    async def upsert(self, channel: discord.abc.Messageable, key: str, embed: discord.Embed, pin: bool = False):
        footer_text = (embed.footer.text or "") if embed.footer else ""
        if f"key:{key}" not in footer_text:
            if embed.footer is None or not embed.footer.text:
                embed.set_footer(text=f"key:{key}")
            else:
                embed.set_footer(text=f"{footer_text} • key:{key}")

        guild_id = getattr(channel, "guild", None).id if getattr(channel, "guild", None) else 0
        channel_id = channel.id

        message_id = self.recall(guild_id, channel_id, key)
        message = None
        if message_id:
            try:
                message = await channel.fetch_message(message_id)
            except Exception:
                message = None

        if message is None:
            message_id = await self._search_existing(channel, key)
            if message_id:
                try:
                    message = await channel.fetch_message(message_id)
                except Exception:
                    message = None

        if message is None:
            message = await channel.send(embed=embed)
            if pin:
                try: await message.pin(reason=f"pin progress embed ({key})")
                except Exception: pass
            self.remember(guild_id, channel_id, key, message.id)
            return message

        try:
            await message.edit(embed=embed)
        except Exception:
            message = await channel.send(embed=embed)
            self.remember(guild_id, channel_id, key, message.id)
        return message
