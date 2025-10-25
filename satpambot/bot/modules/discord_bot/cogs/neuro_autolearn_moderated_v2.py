import os, json, random, asyncio, logging
from pathlib import Path
import discord
from discord.ext import commands, tasks

log = logging.getLogger(__name__)

try:
    from satpambot.ai.persona_injector import build_system
except Exception:
    def build_system(base: str = "") -> str:
        return base or ""

try:
    from satpambot.helpers.llm_clients import QnaClient
except Exception:
    class QnaClient:
        async def answer(self, prompt: str, system: str) -> str:
            return "SMOKE_ANSWER"

QNA_TOPICS_PATH = Path("data/config/qna_topics.json")

def _load_topics():
    try:
        data = json.loads(QNA_TOPICS_PATH.read_text(encoding="utf-8"))
        return [t["q"] if isinstance(t, dict) and "q" in t else str(t) for t in data if t]
    except Exception:
        return ["Sebutkan satu kebiasaan kecil yang bisa meningkatkan produktivitas harianmu."]

class NeuroAutolearnModeratedV2(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.enable = os.getenv("QNA_ENABLE","0") == "1"
        self.interval_min = int(os.getenv("QNA_INTERVAL_MIN","15"))
        self.private_ch_id = None
        self.private_ch_name = (os.getenv("QNA_CHANNEL_NAME") or "").strip() or None
        try:
            ch_id_env = os.getenv("QNA_CHANNEL_ID","").strip()
            self.private_ch_id = int(ch_id_env) if ch_id_env else None
        except Exception:
            self.private_ch_id = None
        self._topics = _load_topics(); random.shuffle(self._topics); self._idx = 0
        self._started = False; self._lock = asyncio.Lock(); self._llm = QnaClient()

    async def _get_qna_channel(self):
        ch = None
        if self.private_ch_id:
            ch = self.bot.get_channel(self.private_ch_id)
            if ch is None:
                try:
                    ch = await self.bot.fetch_channel(self.private_ch_id)
                except Exception as e:
                    log.warning("fetch_channel(%s) failed: %r", self.private_ch_id, e)
        if ch is None and self.private_ch_name:
            try:
                for g in getattr(self.bot, "guilds", []):
                    for c in g.text_channels:
                        if (c.name or "").lower() == self.private_ch_name.lower():
                            ch = c; break
                    if ch: break
            except Exception as e:
                log.warning("search channel by name failed: %r", e)
        return ch

    @commands.Cog.listener()
    async def on_ready(self):
        if not self.enable or self._started: return
        self._started = True
        self.qna_loop.change_interval(minutes=self.interval_min)
        self.qna_loop.start()

    @tasks.loop(minutes=60)
    async def qna_loop(self):
        async with self._lock:
            await self._one_round()

    @qna_loop.before_loop
    async def _before_loop(self):
        try:
            await self.bot.wait_until_ready()
        except Exception:
            pass

    async def _one_round(self, *, force_prompt: str | None = None):
        if not self.enable:
            return
        ch = await self._get_qna_channel()
        if not isinstance(ch, (discord.TextChannel, discord.Thread)):
            log.warning("QNA: channel not found or invalid. Set QNA_CHANNEL_ID or QNA_CHANNEL_NAME.")
            return

        if force_prompt is None:
            if self._idx >= len(self._topics):
                self._idx = 0; random.shuffle(self._topics)
            q = self._topics[self._idx]; self._idx += 1
        else:
            q = force_prompt

        q_embed = discord.Embed(title="Question by Leina", description=q)
        try: q_embed.set_footer(text=f"interval {self.interval_min}m • auto-learn")
        except Exception: pass
        ref = None
        try:
            ref = await ch.send(embed=q_embed)
        except Exception as e:
            log.error("send question failed: %r", e)

        system = build_system("Jawab ringkas, jelas, tidak spam. Jika tidak yakin, minta klarifikasi singkat.")
        try:
            ans = await self._llm.answer(q, system=system)
        except Exception as e:
            log.error("LLM answer error: %r", e)
            ans = "(maaf) sementara belum bisa menjawab."
        a_embed = discord.Embed(title="Answer by Leina", description=ans)
        try:
            await ch.send(embed=a_embed, reference=ref)
        except Exception:
            try:
                await ch.send(embed=a_embed)
            except Exception as e:
                log.error("send answer failed: %r", e)

    @commands.command(name="qna_now", help="Jalankan 1 putaran QnA sekarang")
    async def qna_now(self, ctx: commands.Context):
        await self._one_round()
        try: await ctx.message.add_reaction("✅")
        except Exception: pass

    @commands.command(name="qna_test", help="Tes QnA dengan prompt custom")
    async def qna_test(self, ctx: commands.Context, *, prompt: str):
        await self._one_round(force_prompt=prompt)
        try: await ctx.message.add_reaction("🧪")
        except Exception: pass

async def setup(bot: commands.Bot):
    await bot.add_cog(NeuroAutolearnModeratedV2(bot))
