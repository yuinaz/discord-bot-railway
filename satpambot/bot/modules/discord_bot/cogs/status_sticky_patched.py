from __future__ import annotations
import os
import asyncio
import logging
import discord
from discord.ext import commands, tasks

log = logging.getLogger("satpambot.status_sticky")

def _int_env(name: str, default: int = 0) -> int:
    try:
        v = os.environ.get(name) or ""
        v = v.strip()
        return int(v) if v else default
    except Exception:
        return default

class StatusStickyPatched(commands.Cog):
    """
    Menjaga satu pesan 'status' tetap di-update di channel tertentu.
    NON-BREAKING: kalau channel tidak diset / tidak ditemukan, cog ini diam (tidak error).
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # ID channel bisa diambil dari env; kalau 0 maka fitur nonaktif
        self.channel_id = (
            _int_env("STATUS_STICKY_CHANNEL_ID", 0)
            or _int_env("STATUS_CHANNEL_ID", 0)
            or _int_env("LOG_CHANNEL_ID", 0)
        )
        self._message_id: int | None = None
        self._ready = asyncio.Event()
        self._loop_task.start()

    def cog_unload(self):
        self._loop_task.cancel()

    @commands.Cog.listener()
    async def on_ready(self):
        self._ready.set()
        log.info("[status] on_ready; channel_id=%s", self.channel_id)

    def _compose_content(self) -> str:
        try:
            lat_ms = int(float(getattr(self.bot, "latency", 0.0)) * 1000)
        except Exception:
            lat_ms = 0
        return f":green_circle: SatpamBot online • Latency {lat_ms} ms"

    async def _get_channel(self) -> discord.abc.Messageable | None:
        cid = self.channel_id
        if not cid:
            return None
        ch = self.bot.get_channel(cid)
        if ch:
            return ch
        try:
            ch = await self.bot.fetch_channel(cid)
            return ch
        except Exception:
            log.warning("[status] channel not found (id=%s)", cid)
            return None

    @tasks.loop(seconds=30)
    async def _loop_task(self):
        # jalan periodik untuk memperbarui sticky message
        if not self.channel_id:
            return  # nonaktif bila channel id kosong
        if not self.bot.is_ready():
            return

        ch = await self._get_channel()
        if not ch:
            return

        content = self._compose_content()
        try:
            if self._message_id:
                try:
                    msg = await ch.fetch_message(self._message_id)
                    await msg.edit(content=content)
                    return
                except discord.NotFound:
                    # pesan hilang, kirim baru
                    pass
                except Exception as e:
                    log.debug("[status] fetch/edit failed: %r", e)

            msg = await ch.send(content)
            self._message_id = msg.id
        except Exception as e:
            log.warning("[status] send/edit failed: %r", e)

    @_loop_task.before_loop
    async def _before_loop(self):
        await self._ready.wait()
        await asyncio.sleep(1.0)  # beri napas 1s setelah ready
        # jalankan update pertama
        try:
            ch = await self._get_channel()
            if ch:
                msg = await ch.send(self._compose_content())
                self._message_id = msg.id
        except Exception as e:
            log.debug("[status] first send failed: %r", e)

async def setup(bot: commands.Bot):
    await bot.add_cog(StatusStickyPatched(bot))
