
from discord.ext import commands
import os
import json
import random
import asyncio
import logging
from datetime import datetime, timedelta

import discord
from discord.ext import tasks, commands

log = logging.getLogger(__name__)

DEFAULT_QNA_CHANNEL_ID = int(os.getenv("QNA_CHANNEL_ID", "1426571542627614772"))
DEFAULT_INTERVAL_SECS = int(os.getenv("QNA_AUTOLEARN_INTERVAL", "1800"))  # 30m
DEFAULT_MAX_PER_HOUR = int(os.getenv("QNA_AUTOLEARN_MAX_PER_HOUR", "2"))
DEFAULT_ENABLE = os.getenv("QNA_AUTOLEARN_ENABLE", "1") not in ("0", "false", "False")
SEED_PATH = os.getenv("QNA_AUTOLEARN_SEED_PATH", "data/neuro-lite/qna_autoseed.json")

# Provider env (optional; if not set we'll just ask the built-in QnA cog via channel message)
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# To be super-safe for Render free: spread jitter a bit
def _jitter(base: int, percent: float = 0.1) -> int:
    span = int(base * percent)
    return max(60, base + random.randint(-span, span))

def _load_seeds():
    try:
        with open(SEED_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        seeds = data.get("seeds") or []
        if not isinstance(seeds, list): raise ValueError("seeds must be a list")
        return [s for s in seeds if isinstance(s, str) and s.strip()]
    except Exception as e:
        log.warning("[qna_autolearn] failed to load seeds from %s: %r; using defaults", SEED_PATH, e)
        return [
            "Ringkas poin penting dari kebijakan moderasi server ini.",
            "Apa bedanya phishing gambar vs teks, dan contoh nyata terbaru?",
            "Kapan aman menggunakan auto-moderation dan kapan perlu manual review?",
            "Jelaskan strategi rate limit agar bot aman di shared hosting (Render free).",
            "Bagaimana cara memprioritaskan laporan user secara otomatis?",
            "Apa indikator channel ramai yang beresiko toxic dan cara mitigasinya?",
            "Kasih daftar 5 pertanyaan yang bagus untuk evaluasi performa bot moderasi.",
            "Rancang flow chart singkat untuk proses ban + appeal yang adil."
        ]

class QnAAutoLearnScheduler(commands.Cog):
    """Periodically posts a seed question in the QNA channel and triggers QnA provider.
    If provider ignores bot messages, this cog will self-call provider if available.
    Designed to be gentle with rate limits and optional if API keys missing.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.qna_channel_id = DEFAULT_QNA_CHANNEL_ID
        self.interval_secs = _jitter(DEFAULT_INTERVAL_SECS, 0.15)
        self.max_per_hour = DEFAULT_MAX_PER_HOUR
        self.enabled = DEFAULT_ENABLE
        self._seeds = _load_seeds()
        self._sent_ts = []  # ring buffer timestamps for rate
        self._lock = asyncio.Lock()

        if self.enabled:
            # delay start to let other cogs load
            self.poster.change_interval(seconds=self.interval_secs)
            self.poster.start()
            log.info("[qna_autolearn] scheduler started (interval=%ss, max/hour=%s, seeds=%d)",
                     self.interval_secs, self.max_per_hour, len(self._seeds))
        else:
            log.info("[qna_autolearn] disabled via env QNA_AUTOLEARN_ENABLE=0")

    def cog_unload(self):
        try:
            self.poster.cancel()
        except Exception:
            pass

    def _rate_ok(self) -> bool:
        now = datetime.utcnow()
        one_hour = now - timedelta(hours=1)
        self._sent_ts = [t for t in self._sent_ts if t > one_hour]
        return len(self._sent_ts) < self.max_per_hour

    async def _maybe_call_provider_direct(self, question: str) -> str | None:
        """Try calling built-in QnA cog provider directly if exposed. Otherwise None."""
        # Attempt to import qna_dual_provider and use a helper if it exists.
        try:
            from satpambot.bot.modules.discord_bot.cogs.qna_dual_provider import QnaDualProvider  # type: ignore
        except Exception:
            return None

        # Find loaded instance
        try:
            for cog in self.bot.cogs.values():
                if isinstance(cog, QnaDualProvider):
                    provider = cog
                    break
            else:
                return None
        except Exception:
            return None

        # Try an obvious method names; fall back to None silently
        for meth in ("ask_text", "infer", "answer_text", "ask"):
            fn = getattr(provider, meth, None)
            if callable(fn):
                try:
                    resp = await fn(question=question) if "question" in fn.__code__.co_varnames else await fn(question)
                    if isinstance(resp, str):
                        return resp
                    # some providers return dict
                    if isinstance(resp, dict) and "text" in resp:
                        return str(resp["text"])
                except Exception as e:
                    log.warning("[qna_autolearn] provider.%s failed: %r", meth, e)
        return None

    async def _groq_gemini_fallback(self, question: str) -> str | None:
        """Optional direct API fallback if provider isn't callable. Only runs if keys present.
        Keep super simple to reduce deps; safe to no-op if keys unset.
        """
        # We intentionally avoid external requests here to keep Render free limits safe.
        # If keys present, we still skip, letting the existing QnA provider handle it.
        return None

    @tasks.loop(seconds=999999)  # overwritten in __init__
    async def poster(self):
        if not self.enabled:
            return
        async with self._lock:
            if not self._rate_ok():
                log.debug("[qna_autolearn] rate limit hit; skipping this cycle")
                return
            channel = self.bot.get_channel(self.qna_channel_id)
            if channel is None:
                # attempt fetch
                try:
                    channel = await self.bot.fetch_channel(self.qna_channel_id)
                except Exception as e:
                    log.warning("[qna_autolearn] cannot get QnA channel %s: %r", self.qna_channel_id, e)
                    return

            seed = random.choice(self._seeds)
            q_text = f"[auto-learn]\nQ: {seed}"
            try:
                msg = await channel.send(q_text)
                self._sent_ts.append(datetime.utcnow())
            except Exception as e:
                log.warning("[qna_autolearn] failed to send seed: %r", e)
                return

            # Try to get an answer explicitly if provider ignores bot-authored messages
            try:
                answer = await self._maybe_call_provider_direct(seed)
            except Exception as e:
                log.warning("[qna_autolearn] direct provider call failed: %r", e)
                answer = None

            if answer:
                try:
                    await channel.send(f"A: {answer}")
                except Exception as e:
                    log.warning("[qna_autolearn] failed to post answer: %r", e)

    @poster.before_loop
    async def before_poster(self):
        await self.bot.wait_until_ready()
        # random initial delay 10-60s to avoid competing with other loops
        await asyncio.sleep(random.randint(10, 60))
async def setup(bot):
    # Prefer modern discord.py setup
    await bot.add_cog(QnAAutoLearnScheduler(bot))

def setup_legacy(bot):
    # Legacy synchronous setup for older loaders
    bot.add_cog(QnAAutoLearnScheduler(bot))