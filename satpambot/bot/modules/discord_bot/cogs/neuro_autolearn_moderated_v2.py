import os, json, random, asyncio
from pathlib import Path
import discord
from discord.ext import commands, tasks

def _groq_openai_base() -> str:
    base = os.getenv("OPENAI_BASE_URL", "https://api.groq.com").rstrip("/")
    return base if base.endswith("/openai/v1") else base + "/openai/v1"

try:
    from satpambot.ai.persona_injector import build_system
except Exception:
    def build_system(base: str = "") -> str:
        return base or ""

QNA_TOPICS_PATH = Path("data/config/qna_topics.json")

def _load_topics():
    try:
        data = json.loads(QNA_TOPICS_PATH.read_text(encoding="utf-8"))
        return [t["q"] if isinstance(t, dict) and "q" in t else str(t) for t in data if t]
    except Exception:
        return ["Sebutkan satu kebiasaan kecil yang bisa meningkatkan produktivitas harianmu."]

class LLMClient:
    def __init__(self):
        self.model = os.getenv("GROQ_MODEL","llama-3.1-8b-instant")
        self.api_key = os.getenv("GROQ_API_KEY","")
        self.url = f"{_groq_openai_base().rstrip('/')}/chat/completions"

    async def answer(self, prompt: str, system: str) -> str:
        try:
            import httpx
            headers = {"Authorization": f"Bearer {self.api_key}"}
            payload = {
                "model": self.model,
                "messages": [
                    {"role":"system","content":system},
                    {"role":"user","content":prompt},
                ],
                "temperature": 0.4,
                "max_tokens": 400,
            }
            async with httpx.AsyncClient(timeout=30) as cx:
                r = await cx.post(self.url, headers=headers, json=payload)
            if r.status_code != 200:
                return f"(fallback) LLM {r.status_code}: {r.text[:200]}"
            j = r.json()
            return (j.get("choices",[{}])[0].get("message",{}).get("content") or "").strip()
        except Exception as e:
            return f"(fallback) Maaf, aku belum bisa menjawab sekarang. [{type(e).__name__}]"

class NeuroAutolearnModeratedV2(commands.Cog):
    """QnA tanya→jawab (persona + anti-spam). Start bila QNA_ENABLE=1."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.enable = os.getenv("QNA_ENABLE","0") == "1"
        self.interval_min = int(os.getenv("QNA_INTERVAL_MIN","15"))
        try:
            self.private_ch_id = int(os.getenv("QNA_CHANNEL_ID","1426571542627614772"))
        except Exception:
            self.private_ch_id = 1426571542627614772
        self._topics = _load_topics(); random.shuffle(self._topics); self._idx = 0
        self._started = False; self._lock = asyncio.Lock(); self._llm = LLMClient()

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

    async def _one_round(self):
        ch = self.bot.get_channel(self.private_ch_id)
        if not isinstance(ch, (discord.TextChannel, discord.Thread)):
            return
        if self._idx >= len(self._topics):
            self._idx = 0; random.shuffle(self._topics)
        q = self._topics[self._idx]; self._idx += 1

        q_embed = discord.Embed(title="Question by Leina", description=q)
        try: q_embed.set_footer(text=f"interval {self.interval_min}m • auto-learn")
        except Exception: pass
        ref = None
        try: ref = await ch.send(embed=q_embed)
        except Exception: pass

        system = build_system("Jawab ringkas, jelas, dan tidak spam. Jika tidak yakin, minta klarifikasi singkat.")
        ans = await self._llm.answer(q, system=system)
        a_embed = discord.Embed(title="Answer by Leina", description=ans)
        try:    await ch.send(embed=a_embed, reference=ref)
        except Exception: await ch.send(embed=a_embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(NeuroAutolearnModeratedV2(bot))
