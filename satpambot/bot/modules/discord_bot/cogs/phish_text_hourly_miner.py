from discord.ext import commands
import asyncio
import logging
import random
import re
import time
from typing import Dict, List

import discord
from discord.ext import commands, tasks

try:
    from ..helpers.memory_upsert import upsert_pinned_memory

except Exception:  # pragma: no cover
    upsert_pinned_memory = None

LOG = logging.getLogger(__name__)

# --- Module config (do NOT move to ENV) ---
START_DELAY_SEC = 300
PERIOD_SEC = 3600
PER_CHANNEL_MESSAGES = 200
MAX_EXAMPLES = 120  # keep compact

URL_RE = re.compile(r'https?://\S+')
SUS_WORDS = [
    "nitro", "steam", "free", "gift", "airdrop", "claim", "verify", "invite", "bonus",
    "wallet", "withdraw", "metamask", "auth", "code", "giveaway", "hadiah",
]

def _suspicious_score(text: str) -> int:
    score = 0
    if URL_RE.search(text):
        score += 2
    low = text.lower()
    for w in SUS_WORDS:
        if w in low:
            score += 1
    # simple unicode obfuscation heuristic
    if any('\u200b' <= ch <= '\u206f' for ch in text):
        score += 2
    return score

def _should_skip_channel(ch: discord.abc.GuildChannel) -> bool:
    name = getattr(ch, "name", "") or ""
    ok_names = {"log-botphising", "log-botphishing", "image-phish", "image-phishing"}
    # We DO scan the phishing log channels; but we never delete there.
    return False if name.lower() in ok_names else False

class PhishTextHourlyMiner(commands.Cog):
    """Collect representative phishing-like text examples; stored via pinned memory safely."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._loop_started = False

    def cog_load(self) -> None:
        # sync for smoke friendliness
        pass

    def cog_unload(self) -> None:
        try:
            if self.loop_collect.is_running():
                self.loop_collect.cancel()
        except Exception:
            pass

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        if not self._loop_started:
            jitter = random.uniform(60, 180)
            delay = START_DELAY_SEC + jitter
            LOG.info("[phish_hourly] will start in %.1fs then every %ds", delay, PERIOD_SEC)
            await asyncio.sleep(delay)
            try:
                self.loop_collect.change_interval(seconds=PERIOD_SEC)
                self.loop_collect.start()
                self._loop_started = True
                LOG.info("[phish_hourly] started (delay=%ds, every=%ds, limit=%d)",
                         int(delay), PERIOD_SEC, PER_CHANNEL_MESSAGES)
            except RuntimeError:
                self._loop_started = True

    @tasks.loop(seconds=PERIOD_SEC)
    async def loop_collect(self) -> None:
        try:
            examples = await self._collect_examples()
            payload = {"phish_text": examples, "ts": int(time.time())}
            ok = False
            if upsert_pinned_memory is not None:
                ok = await upsert_pinned_memory(self.bot, payload)
            else:
                LOG.warning("[phish_hourly] memory_upsert helper missing; collected=%d", len(examples))
                ok = True
            LOG.info("[phish_hourly] memory updated: %s", bool(ok))
        except Exception as e:
            LOG.exception("[phish_hourly] error in loop_collect: %r", e)

    async def _collect_examples(self) -> List[Dict[str, str]]:
        found: List[Dict[str, str]] = []
        # Prefer scanning explicit phishing/log channels first
        preferred = []
        others = []
        for guild in list(self.bot.guilds or []):
            for ch in guild.text_channels:
                name = (ch.name or "").lower()
                if "phish" in name or "botphish" in name or "phising" in name:
                    preferred.append(ch)
                else:
                    others.append(ch)

        async def scan_channel(ch: discord.TextChannel):
            try:
                async for msg in ch.history(limit=PER_CHANNEL_MESSAGES, oldest_first=False):
                    if not msg.content:
                        continue
                    score = _suspicious_score(msg.content)
                    if score >= 2:  # keep reasonably suspicious
                        snippet = msg.content.strip().replace("\n", " ")
                        if len(snippet) > 180:
                            snippet = snippet[:177] + "..."
                        found.append({
                            "ch": f"#{ch.name}",
                            "by": getattr(msg.author, "display_name", "unknown"),
                            "score": str(score),
                            "text": snippet,
                            "url": msg.jump_url,
                        })
                        if len(found) >= MAX_EXAMPLES:
                            return
            except discord.Forbidden:
                return
            except discord.HTTPException:
                return

        # Scan preferred first, then others until cap
        for ch in preferred + others:
            if len(found) >= MAX_EXAMPLES:
                break
            await scan_channel(ch)

        return found
async def setup(bot: commands.Bot):
    await bot.add_cog(PhishTextHourlyMiner(bot))