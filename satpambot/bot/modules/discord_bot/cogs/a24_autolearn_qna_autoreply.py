
import os, asyncio, logging, random, json, hashlib, time, re
import discord
from discord.ext import commands, tasks
from urllib.parse import quote as _q

try:
    import httpx
except Exception:
    httpx = None

log = logging.getLogger(__name__)

# === Config ===
QNA_CHANNEL_ID = int(os.getenv("QNA_CHANNEL_ID") or 0) or 1426571542627614772
ASK_INTERVAL_MIN = int(os.getenv("QNA_AUTOASK_INTERVAL_MIN", "7"))
DEDUP_TTL_SEC = int(os.getenv("QNA_ASK_DEDUP_TTL_SEC", "259200"))  # 3 hari
RECENT_MAX = int(os.getenv("QNA_ASK_RECENT_MAX", "200"))
QNA_TOPICS_FILE = os.getenv("QNA_TOPICS_FILE", "data/config/qna_topics.json")
QNA_TOPICS_JSON = os.getenv("QNA_TOPICS_JSON", "")
PROVIDER_ORDER = [s.strip() for s in (os.getenv("QNA_PROVIDER_ORDER") or "groq,gemini").split(",") if s.strip()]

UPSTASH_URL = os.getenv("UPSTASH_REDIS_REST_URL")
UPSTASH_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN")
UPSTASH_NS = os.getenv("QNA_ASK_DEDUP_NS", "qna:recent")

DEFAULT_POOLS = {
    "game": [
        "Bagaimana live-ops ala game Korea menjaga retensi tanpa terasa pay-to-win?",
        "Apa pelajaran onboarding pemain baru dari game Nintendo yang bisa ditiru studio kecil?",
        "Gacha: desain aman agar adil sekaligus berkelanjutan secara bisnis?"
    ],
    "musik": [
        "Bagaimana K-pop mendesain hook 15 detik yang efektif di short-video?"
    ],
    "ai": [
        "Praktik aman memakai AI generatif dalam komunitas online?"
    ],
    "vtuber": [
        "Apakah subtitle otomatis cukup untuk ekspansi global konten VTuber?"
    ],
    "cosplay": [
        "Bagaimana komunitas cosplay Jepang menjaga etik foto dan consent di event?"
    ]
}

def _normalize(text: str) -> str:
    t = text.strip().lower()
    t = re.sub(r"\s+", " ", t)
    return t

def _hash(text: str) -> str:
    return hashlib.sha1(_normalize(text).encode()).hexdigest()

async def _upstash_get(client, key):
    if not (UPSTASH_URL and UPSTASH_TOKEN and client): return None
    try:
        r = await client.get(f"{UPSTASH_URL}/get/{_q(key, safe='')}", headers={"Authorization": f"Bearer {UPSTASH_TOKEN}"})
        if r.status_code == 200:
            return (r.json() or {}).get("result")
    except Exception:
        pass
    return None

async def _upstash_setex(client, key, ttl, val):
    if not (UPSTASH_URL and UPSTASH_TOKEN and client): return False
    try:
        r = await client.post(f"{UPSTASH_URL}/setex/{_q(key,safe='')}/{ttl}/{_q(val,safe='')}", headers={"Authorization": f"Bearer {UPSTASH_TOKEN}"})
        return r.status_code == 200
    except Exception:
        return False

async def _llm_generate(topic: str) -> str:
    # prefer facade if available
    try:
        from ....providers.llm_facade import ask as llm_ask
    except Exception:
        llm_ask = None
    prompt = (
        "Buat SATU pertanyaan singkat, sopan, netral, dan aman untuk komunitas umum. "
        "Topik: " + topic + ". "
        "Jawab HANYA satu kalimat tanya yang berakhir dengan tanda tanya."
    )
    if llm_ask:
        for prov in PROVIDER_ORDER:
            try:
                txt = await llm_ask(
                    provider=prov,
                    model=os.getenv('GROQ_MODEL') if prov=='groq' else os.getenv('GEMINI_MODEL'),
                    system='Kamu generator pertanyaan. Jawab hanya SATU kalimat tanya, tanpa tambahan lain.',
                    messages=[{'role':'user','content': prompt}],
                    temperature=0.8,
                    max_tokens=48
                )
                if txt and txt.strip().endswith('?') and len(_normalize(txt)) >= 12:
                    return txt.strip()
            except Exception:
                continue
    # fallback
    pool = DEFAULT_POOLS.get(topic, [])
    return random.choice(pool) if pool else "Apa yang sedang kamu pikirkan sekarang?"

class AutoAskQnA(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.recent = []  # list[(hash, ts)]
        self._client = httpx.AsyncClient(timeout=8.0) if httpx else None
        self.topics = self._load_topics()
        self._last_topic = None
        self.loop.start()

    def _load_topics(self):
        # 1) Prefer file JSON
        if QNA_TOPICS_FILE and os.path.exists(QNA_TOPICS_FILE):
            try:
                with open(QNA_TOPICS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict) and data:
                    log.info("[qna-autoask] topics loaded from file: %s (keys=%s)", QNA_TOPICS_FILE, list(data.keys()))
                    return data
            except Exception as e:
                log.warning("[qna-autoask] cannot load topics file %s: %r", QNA_TOPICS_FILE, e)
        # 2) Fallback env JSON
        if QNA_TOPICS_JSON:
            try:
                data = json.loads(QNA_TOPICS_JSON)
                if isinstance(data, dict) and data:
                    log.info("[qna-autoask] topics loaded from env JSON (keys=%s)", list(data.keys()))
                    return data
            except Exception as e:
                log.warning("[qna-autoask] invalid QNA_TOPICS_JSON: %r", e)
        # 3) Defaults
        log.info("[qna-autoask] using DEFAULT_POOLS")
        return DEFAULT_POOLS

    def _remember(self, q: str):
        h = _hash(q)
        now = int(time.time())
        self.recent.append((h, now))
        # trim & ttl
        self.recent = [(hh,ts) for hh,ts in self.recent if now-ts < DEDUP_TTL_SEC][-RECENT_MAX:]
        return h

    async def _seen(self, q: str) -> bool:
        h = _hash(q)
        now = int(time.time())
        # in-memory TTL
        self.recent = [(hh,ts) for hh,ts in self.recent if now-ts < DEDUP_TTL_SEC]
        if any(h == hh for hh,_ in self.recent):
            return True
        # Upstash check (best-effort)
        if self._client and UPSTASH_URL and UPSTASH_TOKEN:
            key = f"{UPSTASH_NS}:{h}"
            try:
                val = await _upstash_get(self._client, key)
                if val is not None:
                    return True
            except Exception:
                pass
        return False

    def _pick_topic(self) -> str:
        keys = list(self.topics.keys())
        if not keys:
            return "global"
        # avoid repeating same topic twice if possible
        if self._last_topic and len(keys) > 1 and self._last_topic in keys:
            alt = [k for k in keys if k != self._last_topic]
            topic = random.choice(alt)
        else:
            topic = random.choice(keys)
        self._last_topic = topic
        return topic

    @tasks.loop(minutes=ASK_INTERVAL_MIN)
    async def loop(self):
        try:
            ch = self.bot.get_channel(QNA_CHANNEL_ID)
            if not ch:
                log.warning("[qna-autoask] channel not found: %s", QNA_CHANNEL_ID)
                return
            topic = self._pick_topic()

            # Try up to N attempts to avoid duplicates
            N = 6
            q = None
            for _ in range(N):
                cand = await _llm_generate(topic)
                if not await self._seen(cand):
                    q = cand
                    break
            if not q:
                # fallback sample unique if possible
                candidates = [x for x in sum(self.topics.values(), [])]
                random.shuffle(candidates)
                for cand in candidates[:50]:
                    if not await self._seen(cand):
                        q = cand
                        break
            if not q:
                q = await _llm_generate(topic)  # last resort

            h = self._remember(q)
            if self._client and UPSTASH_URL and UPSTASH_TOKEN:
                await _upstash_setex(self._client, f"{UPSTASH_NS}:{h}", DEDUP_TTL_SEC, str(int(time.time())))

            emb = discord.Embed(title="Question by Leina", description=q)
            await ch.send(embed=emb)
        except Exception as e:
            log.warning("[qna-autoask] %r", e)

    @loop.before_loop
    async def before(self):
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot):
    await bot.add_cog(AutoAskQnA(bot))
