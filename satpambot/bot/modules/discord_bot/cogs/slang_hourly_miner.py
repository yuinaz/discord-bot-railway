# -*- coding: utf-8 -*-
from __future__ import annotations
import re, asyncio, logging, collections
from typing import List, Iterable, Tuple
import discord
from discord.ext import commands, tasks

from satpambot.bot.modules.discord_bot.helpers.memory_upsert import upsert_pinned_memory
from satpambot.bot.modules.discord_bot.config.self_learning_cfg import (
    LOG_CHANNEL_ID, LEARN_ALL_PUBLIC, LEARN_CHANNEL_IDS, LEARN_SCAN_PER_CHANNEL,
    SLANG_FIRST_DELAY_SECONDS, SLANG_INTERVAL_SECONDS
)

log = logging.getLogger(__name__)

STOPWORDS = set("""yang dan di ke dari dengan untuk dalam pada ini itu itu/ituan aja kok tuh kan nya sih si ya saya aku kamu kalian kami kita mereka dia dia/nya gue lu loh lah dong deh pun atau serta para tiap setiap jadi karena sehingga agar supaya belum sudah akan bisa dapat tidak bukan iya iyaaa ok oke okay baik terima kasih makasih makasi makasihhh
selamat pagi siang sore malam halo hai haii assalamualaikum wr wb om swastiastu shalom
""".split())

URL_RE = re.compile(r'https?://[^\s)>\]]+')
MENTION_RE = re.compile(r'<[@#][^>]+>')
EMOJI_RE = re.compile(r'[\U0001F300-\U0001FAFF\u2600-\u26FF]')

def normalize_text(t: str) -> str:
    t = t.lower()
    t = URL_RE.sub(' ', t)
    t = MENTION_RE.sub(' ', t)
    t = re.sub(r'[`*_~>\[\]\(\)\{\}|]', ' ', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t

def tokens(t: str) -> List[str]:
    t = normalize_text(t)
    toks = re.findall(r"[a-z0-9]+|"+EMOJI_RE.pattern, t)
    return [w for w in toks if w and w not in STOPWORDS]

def ngrams(words: List[str], n: int) -> Iterable[Tuple[str,...]]:
    return zip(*(words[i:] for i in range(n)))

def top_counts(counter: collections.Counter, k=50):
    return [[w, int(c)] for w, c in counter.most_common(k)]

def channel_allowlisted(ch: discord.TextChannel) -> bool:
    n = ch.name.lower()
    if ch.id == LOG_CHANNEL_ID:
        return False
    banned = ('mod', 'admin', 'log', 'error', 'staff', 'private', 'nsfw')
    if any(b in n for b in banned):
        return False
    perms = ch.permissions_for(ch.guild.me)
    return bool(perms.read_messages and perms.read_message_history)

class SlangHourlyMiner(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot=bot
        self.loop_task=None

    async def cog_load(self):
        self.loop_task=self.loop_collect.start()

    def cog_unload(self):
        if self.loop_task: self.loop_task.cancel()

    @tasks.loop(seconds=SLANG_INTERVAL_SECONDS)
    async def loop_collect(self):
        await self.bot.wait_until_ready()

        targets: List[discord.TextChannel] = []
        if LEARN_CHANNEL_IDS:
            for i in LEARN_CHANNEL_IDS:
                ch = self.bot.get_channel(i)
                if isinstance(ch, discord.TextChannel) and channel_allowlisted(ch):
                    targets.append(ch)
        elif LEARN_ALL_PUBLIC:
            for g in self.bot.guilds:
                for ch in g.text_channels:
                    if channel_allowlisted(ch):
                        targets.append(ch)

        if not targets:
            log.info("[slang_hourly] no target channels")
            return

        word_ct = collections.Counter()
        emoji_ct = collections.Counter()
        bi_ct = collections.Counter()
        tri_ct = collections.Counter()
        greet_ct = collections.Counter()

        GREET = ('halo','hai','assalamualaikum','selamat','pagi','siang','sore','malam','hello','hi')
        limit = LEARN_SCAN_PER_CHANNEL

        for ch in targets:
            try:
                async for m in ch.history(limit=limit, oldest_first=False):
                    if not m.content:
                        continue
                    toks = tokens(m.content)
                    if not toks:
                        continue
                    word_ct.update([t for t in toks if not EMOJI_RE.fullmatch(t)])
                    emoji_ct.update([t for t in toks if EMOJI_RE.fullmatch(t)])
                    bi_ct.update([' '.join(x) for x in ngrams(toks,2)])
                    tri_ct.update([' '.join(x) for x in ngrams(toks,3)])
                    if any(g in toks for g in GREET):
                        greet_ct.update([g for g in GREET if g in toks])
            except Exception as e:
                log.warning("[slang_hourly] history fail on #%s: %s", ch.name, e)

        lingo = {
            "words_top": top_counts(word_ct, 80),
            "phrases_top": top_counts(tri_ct, 40) + top_counts(bi_ct, 40),
            "emoji_top": top_counts(emoji_ct, 40),
            "greetings": top_counts(greet_ct, 20),
            "source_channels": [getattr(ch,'id',None) for ch in targets][:50],
            "scan_limit_per_channel": limit,
        }
        ok = await upsert_pinned_memory(self.bot, {"lingo": lingo})
        log.info("[slang_hourly] memory updated: %s", ok)

    @loop_collect.before_loop
    async def before_loop(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(SLANG_FIRST_DELAY_SECONDS)
        log.info("[slang_hourly] started (delay=%ss, every=%ss, per_channel=%s)",
                 SLANG_FIRST_DELAY_SECONDS, SLANG_INTERVAL_SECONDS, LEARN_SCAN_PER_CHANNEL)

async def setup(bot):
    await bot.add_cog(SlangHourlyMiner(bot))
