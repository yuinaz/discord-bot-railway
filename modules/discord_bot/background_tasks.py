import asyncio
import logging
import discord
from datetime import datetime

_start_time = datetime.utcnow()

def get_uptime():
    delta = datetime.utcnow() - _start_time
    return str(delta).split('.')[0]

def run_background_tasks(bot):
    async def status_task():
        await bot.wait_until_ready()
        while not bot.is_closed():
            uptime = get_uptime()
            try:
                await bot.change_presence(status=discord.Status.online, activity=discord.Game(name="Menjaga Server Dari Scam"))
            except Exception as e:
                logging.error(f"❌ Gagal update status bot: {e}")
            await asyncio.sleep(60)

    bot.loop.create_task(status_task())
