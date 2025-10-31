from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import List, Optional

import discord
from discord.ext import commands

log = logging.getLogger(__name__)

# ===== Config via ENV =====
ENABLE = os.getenv("QNA_AUTOLEARN_ENABLE", "1") == "1"
SMOKE_MODE = os.getenv("SMOKE_TEST", "0") == "1" or os.getenv("UNIT_TEST", "0") == "1" or os.getenv("CI", "0") == "1"

INTERVAL_SEC = int(os.getenv("QNA_INTERVAL_SEC", "180"))  # user asked for ~3 minutes
QNA_CH_ID = int(os.getenv("QNA_CHANNEL_ID", "0") or 0)    # MUST use this key (not QNA_ISOLATED_ID)
QNA_CH_NAME = os.getenv("QNA_CHANNEL_NAME", "").strip()

QNA_EMBED_TITLE_QUESTION = os.getenv("QNA_EMBED_TITLE_QUESTION", "Question by Leina")
QNA_TOPICS_PATH = os.getenv("QNA_TOPICS_PATH", "data/config/qna_topics.json")  # do not modify/remove file; just read

ALLOWED_MENTIONS = discord.AllowedMentions.none()


class QnAAutoLearnScheduler(commands.Cog):
    """
    Periodically post QnA seed questions in the isolation channel.
    - Safe on import (no side effects)
    - Starts only on_ready
    - Uses ENV QNA_CHANNEL_ID or fallback QNA_CHANNEL_NAME
    - Respects SMOKE/UNIT/CI flags
    - No spam: interval-based, single runner
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.interval_sec = INTERVAL_SEC   # ensure attribute exists (fixes AttributeError)
        self._task: Optional[asyncio.Task] = None
        self._stop = asyncio.Event()
        self._busy = asyncio.Lock()
        self._topics: List[str] = []
        self._idx = 0

    async def cog_load(self) -> None:
        if not ENABLE or SMOKE_MODE:
            log.info("[qna-autolearn] disabled (ENABLE=%s SMOKE=%s)", ENABLE, SMOKE_MODE)
            return
        # pre-load topics once
        self._topics = await self._load_topics()
        log.info("[qna-autolearn] loaded %d topics", len(self._topics))

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        if not ENABLE or SMOKE_MODE:
            return
        if self._task is None or self._task.done():
            self._stop.clear()
            self._task = self.bot.loop.create_task(self._runner(), name="qna_autolearn_scheduler")
            log.info("[qna-autolearn] background scheduler started (interval=%ss)", self.interval_sec)

    async def cog_unload(self) -> None:
        if self._task and not self._task.done():
            self._stop.set()
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            log.info("[qna-autolearn] scheduler stopped")

    # ===== Admin commands =====
    @commands.group(name="qna_auto", invoke_without_command=True)
    @commands.is_owner()
    async def qna_auto_group(self, ctx: commands.Context):
        ch = await self._resolve_channel()
        await ctx.send(f"[qna-autolearn] enable={ENABLE} smoke={SMOKE_MODE} interval={self.interval_sec}s "
                       f"channel={'OK' if ch else 'MISSING'} topics={len(self._topics)} idx={self._idx}")

    @qna_auto_group.command(name="next")
    @commands.is_owner()
    async def qna_auto_next(self, ctx: commands.Context):
        """Send next seed immediately (one-shot)."""
        ok = await self._send_next_seed()
        await ctx.send(f"[qna-autolearn] next -> {'OK' if ok else 'FAIL'}")

    @qna_auto_group.command(name="reload")
    @commands.is_owner()
    async def qna_auto_reload(self, ctx: commands.Context):
        self._topics = await self._load_topics()
        self._idx = 0
        await ctx.send(f"[qna-autolearn] topics reloaded: {len(self._topics)} items")

    # ===== Runner =====
    async def _runner(self):
        # small warmup to let caches/guilds resolve
        await asyncio.sleep(5)
        while not self._stop.is_set():
            try:
                await self._send_next_seed()
            except Exception:
                log.exception("[qna-autolearn] unhandled error in tick")
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=self.interval_sec)
            except asyncio.TimeoutError:
                pass

    async def _send_next_seed(self) -> bool:
        if not self._topics:
            # reload on the fly
            self._topics = await self._load_topics()
            if not self._topics:
                log.warning("[qna-autolearn] topics empty -> skip")
                return False

        ch = await self._resolve_channel()
        if not ch:
            log.warning("[qna-autolearn] channel not found. Set QNA_CHANNEL_ID or QNA_CHANNEL_NAME.")
            return False

        async with self._busy:  # prevent overlap
            question = self._topics[self._idx % len(self._topics)]
            self._idx += 1

            embed = discord.Embed(title=QNA_EMBED_TITLE_QUESTION, description=str(question), colour=0x2b90d9)
            embed.set_footer(text="Auto-learn seed • QnA isolation channel")
            try:
                await ch.send(embed=embed, allowed_mentions=ALLOWED_MENTIONS)
                log.info("[qna-autolearn] sent seed: %s", question[:80])
                return True
            except Exception as e:
                log.warning("[qna-autolearn] failed to send seed embed: %r", e)
                return False

    # ===== Helpers =====
    async def _resolve_channel(self) -> Optional[discord.TextChannel]:
        if QNA_CH_ID:
            ch = self.bot.get_channel(QNA_CH_ID)
            if isinstance(ch, discord.TextChannel):
                return ch
            try:
                ch = await self.bot.fetch_channel(QNA_CH_ID)
                if isinstance(ch, discord.TextChannel):
                    return ch
            except Exception:
                pass
        if QNA_CH_NAME:
            # fallback by name (first match)
            for guild in self.bot.guilds:
                for ch in guild.text_channels:
                    if ch.name == QNA_CH_NAME:
                        return ch
        return None

    async def _load_topics(self) -> List[str]:
        path = self._resolve_topics_path()
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
            data = json.loads(text)
            # accept list of strings or objects with "q" field
            if isinstance(data, list):
                out = []
                for item in data:
                    if isinstance(item, str):
                        out.append(item)
                    elif isinstance(item, dict) and "q" in item:
                        out.append(str(item["q"]))
                return [x for x in out if x]
            log.warning("[qna-autolearn] qna_topics.json format is not a list -> empty")
            return []
        except FileNotFoundError:
            log.warning("[qna-autolearn] topics file not found at %s", path)
            return []
        except Exception:
            log.exception("[qna-autolearn] failed to load topics")
            return []

    def _resolve_topics_path(self) -> Path:
        # try env path (absolute or relative to repo root)
        p = Path(QNA_TOPICS_PATH)
        if p.is_file():
            return p
        # derive repo root from this file location
        here = Path(__file__).resolve()
        # go up until we find 'data' directory
        for parent in [here] + list(here.parents):
            candidate = parent / "data" / "config" / "qna_topics.json"
            if candidate.is_file():
                return candidate
        # default fallback
        return Path("data/config/qna_topics.json")


async def setup(bot: commands.Bot):
    if not ENABLE or SMOKE_MODE:
        log.info("[qna-autolearn] extension loaded but disabled (ENABLE=%s SMOKE=%s)", ENABLE, SMOKE_MODE)
    await bot.add_cog(QnAAutoLearnScheduler(bot))
