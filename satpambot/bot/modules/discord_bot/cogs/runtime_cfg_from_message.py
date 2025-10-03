from __future__ import annotations
import logging, json, re
import discord
from discord.ext import commands
from satpambot.bot.modules.discord_bot.helpers.runtime_cfg import ConfigManager

log = logging.getLogger(__name__)

def _extract_json_from_text(text: str):
    if not text: return None
    m = re.search(r"```(?:json\s*)?(.*?)```", text, re.S|re.I)
    if m:
        raw = m.group(1).strip()
        try: return json.loads(raw)
        except Exception: pass
    try: return json.loads(text)
    except Exception: return None

class RuntimeCfgFromMessage(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.cfg = ConfigManager.instance()
        self._last_payload = None

    async def _apply(self):
        ch_id = self.cfg.get("config_source.channel_id")
        msg_id = self.cfg.get("config_source.message_id")
        if not ch_id or not msg_id: 
            return
        try:
            ch = self.bot.get_channel(int(ch_id)) or await self.bot.fetch_channel(int(ch_id))
            msg = await ch.fetch_message(int(msg_id))
        except Exception as e:
            log.info("[cfg-msg] fetch gagal: %r", e); return
        data = _extract_json_from_text(getattr(msg, "content", ""))
        if data is None:
            return
        payload = json.dumps(data, sort_keys=True)
        if payload == self._last_payload:
            return
        cur = self.cfg._data.copy()
        for k, v in data.items():
            cur[k] = v
        self.cfg.set("", cur)
        self._last_payload = payload
        log.info("[cfg-msg] runtime config di-update dari pesan %s", msg_id)

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        await self._apply()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
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
        await self._apply()

    @commands.Cog.listener()
    async def on_ready(self):
        await self._apply()

async def setup(bot: commands.Bot):
    await bot.add_cog(RuntimeCfgFromMessage(bot))
