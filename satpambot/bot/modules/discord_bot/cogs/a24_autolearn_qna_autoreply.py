import os, asyncio, logging, time, json, random
import discord
from discord.ext import commands, tasks

logger = logging.getLogger(__name__)

def _env(name, default=None):
    v = os.environ.get(name)
    return v if v not in (None, "") else default

def _qna_channel_id(bot):
    env_id = _env("QNA_CHANNEL_ID")
    if env_id and str(env_id).isdigit():
        return int(env_id)
    return getattr(bot, "QNA_CHANNEL_ID", None)

async def _upstash_set(key, val):
    url = os.environ.get("UPSTASH_REDIS_REST_URL")
    tok = os.environ.get("UPSTASH_REDIS_REST_TOKEN")
    if not (url and tok): 
        return False
    import httpx
    headers={"Authorization": f"Bearer {tok}", "Content-Type":"application/json"}
    body=["SET", key, json.dumps(val)]
    async with httpx.AsyncClient(timeout=5.0) as x:
        r = await x.post(url, headers=headers, json=body)
        return r.status_code == 200

async def _upstash_get(key):
    url = os.environ.get("UPSTASH_REDIS_REST_URL")
    tok = os.environ.get("UPSTASH_REDIS_REST_TOKEN")
    if not (url and tok): 
        return None
    import httpx
    headers={"Authorization": f"Bearer {tok}", "Content-Type":"application/json"}
    body=["GET", key]
    async with httpx.AsyncClient(timeout=5.0) as x:
        r = await x.post(url, headers=headers, json=body)
        if r.status_code != 200: 
            return None
        try:
            data = r.json().get("result")
            return json.loads(data) if isinstance(data, str) else data
        except Exception:
            return None

_QUESTIONS = [
    "Apa aturan keselamatan dasar ketika menerima DM dari orang tak dikenal?",
    "Bagaimana cara melaporkan konten phishing di server ini?",
    "Kapan bot harus diam (tidak menjawab) di public channel?",
    "Apa langkah cepat memeriksa tautan mencurigakan sebelum diklik?",
    "Jelaskan peran QnA channel dan bagaimana bot belajar dari sana."
]

class AutoLearnQnaAutoReply(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._mem_last = {"q": None, "ts": 0.0}
        self.loop_task.start()

    def cog_unload(self):
        try:
            self.loop_task.cancel()
        except Exception:
            pass

    @tasks.loop(seconds=75.0)
    async def loop_task(self):
        ch_id = _qna_channel_id(self.bot)
        if not ch_id:
            return
        channel = self.bot.get_channel(ch_id)
        if not isinstance(channel, discord.TextChannel):
            return

        now = time.time()
        try:
            state = await _upstash_get("autolearn:last_question") or self._mem_last
        except Exception:
            state = self._mem_last
        last_ts = float(state.get("ts", 0.0))
        if now - last_ts < 120:  # 2 minutes anti-spam
            return

        q = random.choice(_QUESTIONS)
        if q == state.get("q"):
            q = random.choice(_QUESTIONS)

        embed_q = discord.Embed(title="Question", description=q, color=0x3C78D8)
        embed_q.set_footer(text="Autolearn · QnA")
        msg = await channel.send(embed=embed_q)

        new_state = {"q": q, "ts": now}
        self._mem_last = new_state
        try:
            await _upstash_set("autolearn:last_question", new_state)
        except Exception:
            pass

        try:
            other = self.bot.get_cog("AutoLearnQnaAnswer")
            if other:
                await other.try_answer(channel, msg)
        except Exception as e:
            logger.warning("[autolearn] answer trigger failed: %r", e)

    @loop_task.before_loop
    async def before(self):
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot):
    await bot.add_cog(AutoLearnQnaAutoReply(bot))
