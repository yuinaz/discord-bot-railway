# satpambot/bot/modules/discord_bot/cogs/imagephish_ref_indexer.py
import io, json, asyncio, math
from typing import Set
from PIL import Image
import discord
from discord.ext import commands

LOG_CHANNEL_NAME = "log-botphising"
REF_THREAD_NAME  = "imagephising"
SATPAM_DB_PREFIX = "SATPAMBOT_PHASH_DB_V1"
RUNTIME_DUMP     = "data/runtime_phash_cache.json"  # optional

def _get_lanczos():
    # Pillow compatibility
    Resampling = getattr(Image, "Resampling", None)
    if Resampling is not None:
        return Resampling.LANCZOS
    return Image.LANCZOS

def _phash64_hex(img: Image.Image) -> str:
    """Simple 64-bit pHash (DCT 8x8 low-frequency). Pure-Python (fast enough for startup scan)."""
    import math
    img = img.convert("L").resize((32, 32), _get_lanczos())
    px = list(img.getdata())
    px = [px[i*32:(i+1)*32] for i in range(32)]
    N, K = 32, 8
    cosx = [[math.cos(math.pi*(2*x+1)*u/(2*N)) for x in range(N)] for u in range(K)]
    cosy = [[math.cos(math.pi*(2*y+1)*v/(2*N)) for y in range(N)] for v in range(K)]
    alpha = [math.sqrt(1/N)] + [math.sqrt(2/N)]*(K-1)
    # separable DCT
    tmp = [[0.0]*N for _ in range(K)]
    for u in range(K):
        for y in range(N):
            s = 0.0
            row = [px[x][y] for x in range(N)]
            for x in range(N):
                s += cosx[u][x] * row[x]
            tmp[u][y] = s
    F = [[0.0]*K for _ in range(K)]
    for u in range(K):
        for v in range(K):
            s = 0.0
            for y in range(N):
                s += tmp[u][y] * cosy[v][y]
            F[u][v] = alpha[u]*alpha[v]*s
    # threshold by median (ignore DC)
    flat = [F[u][v] for u in range(K) for v in range(K)]
    flat[0] = 0.0
    med = sorted(flat)[len(flat)//2]
    bits = []
    for u in range(K):
        for v in range(K):
            bits.append(1 if F[u][v] > med else 0)
    v = 0
    for b in bits:
        v = (v << 1) | b
    return f"{v:016x}"

class ImagePhishRefIndexer(commands.Cog):
    """Build pHash cache from thread `imagephising` + JSON message in #log-botphising."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.ref_phash: Set[str] = set()
        self.ready = asyncio.Event()

    @commands.Cog.listener()
    async def on_ready(self):
        if self.ready.is_set():
            return
        try:
            await self._build_cache()
        finally:
            self.ready.set()

    async def _build_cache(self):
        if not self.bot.guilds:
            return
        guild: discord.Guild = self.bot.guilds[0]
        log_ch = discord.utils.get(guild.text_channels, name=LOG_CHANNEL_NAME)
        if not log_ch:
            print(f"[ref_indexer] log channel '{LOG_CHANNEL_NAME}' not found")
            return

        # 1) parse JSON DB messages (SATPAMBOT_PHASH_DB_V1 ... {json})
        async for m in log_ch.history(limit=400):
            if not m.content:
                continue
            if m.content.startswith(SATPAM_DB_PREFIX):
                idx = m.content.find("{")
                if idx >= 0:
                    try:
                        db = json.loads(m.content[idx:])
                        for h in db.get("phash", []):
                            if isinstance(h, str) and len(h) == 16:
                                self.ref_phash.add(h.lower())
                    except Exception:
                        pass

        # 2) scan thread imagephising (active + archived)
        ref_thread = None
        for t in list(log_ch.threads):
            if t.name.lower() == REF_THREAD_NAME.lower():
                ref_thread = t; break
        if not ref_thread:
            async for t in log_ch.archived_threads(limit=100):
                if t.name.lower() == REF_THREAD_NAME.lower():
                    ref_thread = t; break

        if ref_thread:
            async for msg in ref_thread.history(limit=None, oldest_first=True):
                for att in msg.attachments:
                    try:
                        if att.content_type and not att.content_type.startswith("image"):
                            continue
                        data = await att.read()
                        img = Image.open(io.BytesIO(data))
                        h = _phash64_hex(img)
                        self.ref_phash.add(h)
                    except Exception:
                        continue

        # 3) optional dump to file (ignore errors)
        try:
            os.makedirs(os.path.dirname(RUNTIME_DUMP), exist_ok=True)
            with open(RUNTIME_DUMP, "w", encoding="utf-8") as f:
                json.dump({"bits":64,"count":len(self.ref_phash),"phash":sorted(self.ref_phash)}, f, indent=2)
        except Exception:
            pass

        print(f"[ref_indexer] total pHash cached: {len(self.ref_phash)}")

async def setup(bot: commands.Bot):
    await bot.add_cog(ImagePhishRefIndexer(bot))