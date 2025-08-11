import logging
import discord
import pytz
from datetime import datetime
from discord.ext import commands

# Inisialisasi logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Zona waktu lokal (WIB)
WIB = pytz.timezone("Asia/Jakarta")

def get_local_time():
    """Mengembalikan waktu lokal dalam format string."""
    return datetime.now(WIB).strftime("%Y-%m-%d %H:%M:%S")

async def send_error_log(channel: discord.TextChannel, title: str, description: str, color=discord.Color.red()):
    """Mengirimkan log error ke channel Discord dalam bentuk embed."""
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.now(WIB)  # Gunakan waktu lokal
    )
    embed.set_footer(text=f"📅 {get_local_time()} WIB")
    await channel.send(embed=embed)

async def send_info_log(channel: discord.TextChannel, title: str, description: str, color=discord.Color.blue()):
    """Mengirimkan log info ke channel Discord dalam bentuk embed."""
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.now(WIB)  # Gunakan waktu lokal
    )
    embed.set_footer(text=f"📅 {get_local_time()} WIB")
    await channel.send(embed=embed)

async def send_warning_log(channel: discord.TextChannel, title: str, description: str, color=discord.Color.gold()):
    """Mengirimkan log warning ke channel Discord dalam bentuk embed."""
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.now(WIB)  # Gunakan waktu lokal
    )
    embed.set_footer(text=f"📅 {get_local_time()} WIB")
    await channel.send(embed=embed)

def log_error(message: str):
    logger.error(f"[{get_local_time()} WIB] {message}")

def log_info(message: str):
    logger.info(f"[{get_local_time()} WIB] {message}")

def log_warning(message: str):
    logger.warning(f"[{get_local_time()} WIB] {message}")
