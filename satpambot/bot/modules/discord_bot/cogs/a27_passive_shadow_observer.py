from __future__ import annotations

from discord.ext import commands
import asyncio, logging, os, re
from typing import Optional, Iterable
import discord

from discord.ext import tasks
from satpambot.bot.modules.discord_bot.helpers.phase_utils import get_phase, add_tk_xp, add_senior_xp, upstash_set, upstash_get

log = logging.getLogger(__name__)

# Config
SHADOW_ENABLE = os.getenv("SHADOW_ENABLE", "1") not in ("0","false","off")
SHADOW_BACKFILL_ENABLE = os.getenv("SHADOW_BACKFILL_ENABLE", "1") not in ("0","false","off")
SHADOW_CHANNEL_INCLUDE = {int(x) for x in os.getenv("SHADOW_CHANNEL_INCLUDE","").split(",") if x.strip().isdigit()}
SHADOW_CHANNEL_EXCLUDE = {int(x) for x in os.getenv("SHADOW_CHANNEL_EXCLUDE","").split(",") if x.strip().isdigit()}
SHADOW_PER_MSG_XP = int(os.getenv("SHADOW_PER_MSG_XP", "1"))
SHADOW_MIN_LEN = int(os.getenv("SHADOW_MIN_LEN", "8"))
SHADOW_MIN_WORDS = int(os.getenv("SHADOW_MIN_WORDS", "2"))
BACKFILL_BATCH = int(os.getenv("BACKFILL_BATCH", "200"))
BACKFILL_SLEEP_S = float(os.getenv("BACKFILL_SLEEP_S", "1.2"))
BACKFILL_KEY_PREFIX = os.getenv("BACKFILL_KEY_PREFIX", "shadow:last")

def _eligible_channel(ch: discord.TextChannel) -> bool:
    if SHADOW_CHANNEL_INCLUDE and ch.id not in SHADOW_CHANNEL_INCLUDE:
        return False
    if ch.id in SHADOW_CHANNEL_EXCLUDE:
        return False
    perms = ch.permissions_for(ch.guild.me) if ch.guild and ch.guild.me else None
    return bool(perms and perms.read_message_history and perms.read_messages)

def _should_count(msg: discord.Message) -> bool:
    if msg.author.bot: return False
    if msg.type != discord.MessageType.default: return False
    if isinstance(msg.channel, discord.DMChannel): return False
    txt = msg.content or ""
    if len(txt) < SHADOW_MIN_LEN: return False
    if len(re.findall(r"\w+", txt)) < SHADOW_MIN_WORDS: return False
    return True

def _add_phase_xp(delta: int):
    phase = get_phase().lower()
    if phase == "senior":
        return add_senior_xp(delta)
    return add_tk_xp(delta)

class PassiveShadowObserver(commands.Cog):
    """Membaca SEMUA chat secara pasif (tanpa reply), menaikkan XP sesuai phase.
    - on_message: menaikkan XP untuk pesan yang lolos heuristik.
    - backfill_loop: saat startup, memindai history lama (per channel) dan mencatat bookmark di Upstash.
    """
    def __init__(self, bot):
        self.bot = bot
        if SHADOW_BACKFILL_ENABLE:
            self.backfill_loop.start()

    def cog_unload(self):
        try: self.backfill_loop.cancel()
        except Exception: pass

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        if not SHADOW_ENABLE: return
        try:
            if not _should_count(msg): return
            if not isinstance(msg.channel, discord.TextChannel): return
            if not _eligible_channel(msg.channel): return
            _add_phase_xp(SHADOW_PER_MSG_XP)
        except Exception as e:
            log.debug("[shadow] on_message skip: %r", e)

    @tasks.loop(minutes=10.0)
    async def backfill_loop(self):
        try:
            for guild in self.bot.guilds:
                me = guild.me
                if not me: continue
                for ch in guild.text_channels:
                    if not _eligible_channel(ch): continue
                    key = f"{BACKFILL_KEY_PREFIX}:{guild.id}:{ch.id}"
                    last_txt, _ = upstash_get(key)
                    last_id = int(last_txt) if (last_txt and last_txt.isdigit()) else None
                    try:
                        fetched = 0
                        async for m in ch.history(limit=BACKFILL_BATCH, oldest_first=True):
                            if last_id and m.id <= last_id:
                                continue
                            if _should_count(m):
                                _add_phase_xp(SHADOW_PER_MSG_XP)
                            fetched += 1
                            if fetched % 50 == 0:
                                await asyncio.sleep(BACKFILL_SLEEP_S)
                        if fetched > 0:
                            upstash_set(key, str(ch.last_message_id or 0))
                            await asyncio.sleep(BACKFILL_SLEEP_S)
                    except discord.Forbidden:
                        continue
                    except Exception as e:
                        log.debug("[shadow] backfill ch=%s err=%r", ch.id, e)
                        await asyncio.sleep(0.5)
        except Exception as e:
            log.warning("[shadow] backfill sweep error: %r", e)

    @backfill_loop.before_loop
    async def _wait_ready(self):
        await self.bot.wait_until_ready()
async def setup(bot):
    await bot.add_cog(PassiveShadowObserver(bot))