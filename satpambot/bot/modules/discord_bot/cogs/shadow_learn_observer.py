
import os, re, random
import discord
from discord.ext import commands, tasks
from satpambot.config.compat_conf import get as cfg
from satpambot.ml import shadow_metrics as sm
from satpambot.ml import groq_helper as gh
from satpambot.ml import neuro_lite_memory_fix as nmem

ENABLED = bool(cfg("SHADOW_LEARN_ENABLED", True, bool))
COUNT_DM_SUMMARY = bool(cfg("SHADOW_DM_SUMMARY", False, bool))
OWNER_ID = int(cfg("SHADOW_DM_OWNER_ID", 0, int) or 0)
PHISH_THREAD_HINTS = [s.strip().lower() for s in cfg("PHISH_THREAD_KEYWORDS", "imagephish,phishing,phish-lab", str).split(",") if s.strip()]
GROQ_WHEN_UNSURE = bool(cfg("SHADOW_GROQ_WHEN_UNSURE", True, bool))
GROQ_SAMPLE_RATE = float(cfg("SHADOW_GROQ_SAMPLE_RATE", 0.01, float))
SMOKE_MODE = bool(cfg("SMOKE_MODE", False, bool))
ALLOW_GROQ_ON_RENDER = bool(cfg("ALLOW_GROQ_ON_RENDER", False, bool))
LINK_RE = re.compile(r"https?://\S+", re.I)

class ShadowLearnObserver(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        if ENABLED and not SMOKE_MODE:
            self.daily_rollup.start()
            self.daily_summary.start()

    def cog_unload(self):
        try: self.daily_rollup.cancel()
        except Exception: pass
        try: self.daily_summary.cancel()
        except Exception: pass

    @commands.Cog.listener()
    async def on_message(self, m: discord.Message):
        if not ENABLED: return
        if m.author.bot or m.guild is None: return
        sm.bump("exposures_total", 1.0, user_id=m.author.id)
        if m.attachments: sm.bump("exposures_with_images", 1.0)
        if LINK_RE.search(m.content or ""): sm.bump("exposures_with_links", 1.0)
        chname = (getattr(m.channel, "name", "") or "").lower()
        if any(k in chname for k in PHISH_THREAD_HINTS): sm.bump("exposures_in_phish_threads", 1.0)

        if GROQ_WHEN_UNSURE and gh.GROQ_API_KEY:
            on_render = bool(os.environ.get("RENDER"))
            if (not on_render) or (on_render and ALLOW_GROQ_ON_RENDER):
                ambiguous = (m.attachments and LINK_RE.search(m.content or "")) or len(m.content or "") > 300
                if ambiguous and random.random() < max(0.0, min(1.0, GROQ_SAMPLE_RATE)):
                    q = f"Give 3 bullet rules to identify if the following content could be phishing or unsafe in Discord. Only bullets. Content: {m.content[:900]}"
                    ans = gh.ask_system(q)
                    if ans: sm.bump("groq_queries", 1.0)

    @tasks.loop(hours=6)
    async def daily_rollup(self):
        nmem.ensure_files()
        sm.rollup_to_progress()

    @daily_rollup.before_loop
    async def before_roll(self):
        await self.bot.wait_until_ready()

    @tasks.loop(hours=24)
    async def daily_summary(self):
        if not COUNT_DM_SUMMARY or not OWNER_ID: return
        try:
            j = nmem.load_junior()
            u = self.bot.get_user(OWNER_ID) or await self.bot.fetch_user(OWNER_ID)
            if u: await u.send(f"[shadow-learn] Junior overall: {j.get('overall', 0)}% | TK:{j['TK']} | SD(L1..L4): {j['SD']}")
        except Exception:
            pass

    @daily_summary.before_loop
    async def before_sum(self):
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot):
    await bot.add_cog(ShadowLearnObserver(bot))
