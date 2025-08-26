
from __future__ import annotations
import discord, io, logging, os, json, asyncio
from discord.ext import commands, tasks
from PIL import Image
import imagehash

log = logging.getLogger(__name__)

PHISH_IMG_DB = os.getenv("PHISH_IMG_DB", "data/phish_phash.json")
PHISH_CONFIG_PATH = os.getenv("PHISH_CONFIG_PATH", "data/phish_config.json")

PHASH_MIRROR_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "1400375184048787566"))
PHASH_MARKER = "SATPAMBOT_PHASH_DB_V1"

def _load_json(path:str)->dict:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _hamming(a:str,b:str)->int:
    try:
        return bin(int(a,16) ^ int(b,16)).count("1")
    except Exception:
        return 999

def _coerce_list(j):
    if isinstance(j, dict) and "phash" in j and isinstance(j["phash"], list):
        return [str(x) for x in j["phash"]]
    if isinstance(j, list):
        return [str(x) for x in j]
    return []

async def _fetch_http_phash() -> list[str]:
    # Try aiohttp, then requests, then urllib
    urls = []
    port = os.getenv("PORT", "5000")
    urls.append(f"http://127.0.0.1:{port}/api/phish/phash")
    urls.append(f"http://localhost:{port}/api/phish/phash")
    urls.append("http://127.0.0.1:3115/api/phish/phash")
    # 1) aiohttp
    try:
        import aiohttp
        async with aiohttp.ClientSession() as s:
            for u in urls:
                try:
                    async with s.get(u, timeout=3) as r:
                        if r.status == 200:
                            return _coerce_list(await r.json())
                except Exception:
                    continue
    except Exception:
        pass
    # 2) requests
    try:
        import requests  # type: ignore
        for u in urls:
            try:
                r = requests.get(u, timeout=3)
                if r.status_code == 200:
                    return _coerce_list(r.json())
            except Exception:
                continue
    except Exception:
        pass
    # 3) urllib
    try:
        import urllib.request, urllib.error  # type: ignore
        for u in urls:
            try:
                with urllib.request.urlopen(u, timeout=3) as fp:
                    data = fp.read()
                return _coerce_list(json.loads(data.decode("utf-8", "ignore")))
            except Exception:
                continue
    except Exception:
        pass
    return []

class AntiImagePhishGuard(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = {"phash": []}
        self.threshold = 8
        self.autoban = False
        cfg = _load_json(PHISH_CONFIG_PATH)
        self.threshold = int(cfg.get("threshold", self.threshold))
        self.autoban = bool(cfg.get("autoban", self.autoban))
        self._refresh_task.start()

    async def _read_from_discord(self) -> list[str]:
        try:
            ch = self.bot.get_channel(int(PHASH_MIRROR_CHANNEL_ID))
            if not isinstance(ch, discord.TextChannel): return []
            pins = await ch.pins()
            for m in pins:
                if m.author.id == self.bot.user.id and m.content and PHASH_MARKER in m.content:
                    txt = m.content
                    start = txt.find("```json")
                    if start == -1: start = txt.find("```")
                    if start != -1:
                        end = txt.rfind("```")
                        payload = txt[start+7:end] if txt.startswith("```json") else txt[start+3:end]
                    else:
                        payload = txt
                    try:
                        return _coerce_list(json.loads(payload))
                    except Exception:
                        return []
        except Exception:
            pass
        return []

    async def _write_to_discord(self, ph: list[str]) -> None:
        try:
            ch = self.bot.get_channel(int(PHASH_MIRROR_CHANNEL_ID))
            if not isinstance(ch, discord.TextChannel): return
            pins = await ch.pins()
            msg = None
            for m in pins:
                if m.author.id == self.bot.user.id and PHASH_MARKER in (m.content or ""):
                    msg = m; break
            payload = {"phash": list(ph)}
            content = f"{PHASH_MARKER}\n```json\n{json.dumps(payload, ensure_ascii=False, separators=(',', ':'))}\n```"
            if msg:
                await msg.edit(content=content, allowed_mentions=discord.AllowedMentions.none())
            else:
                msg = await ch.send(content=content, allowed_mentions=discord.AllowedMentions.none())
                try: await msg.pin()
                except Exception: pass
        except Exception:
            pass

    async def _refresh_once(self):
        file_ph = []
        http_ph = []
        disc_ph = []

        j = _load_json(PHISH_IMG_DB)
        if isinstance(j, dict) and isinstance(j.get("phash"), list):
            file_ph = [str(x) for x in j["phash"]]

        if not file_ph:
            try:
                http_ph = await _fetch_http_phash()
            except Exception:
                http_ph = []

        if not file_ph and not http_ph:
            try:
                disc_ph = await self._read_from_discord()
            except Exception:
                disc_ph = []

        merged = []
        for src in (file_ph, http_ph, disc_ph):
            for h in src:
                if h not in merged:
                    merged.append(h)
        self.db["phash"] = merged

        # mirror back if we have any
        if merged:
            await self._write_to_discord(merged)

        log.info("[phish] refresh: file=%d http=%d discord=%d total=%d threshold=%d autoban=%s",
                 len(file_ph), len(http_ph), len(disc_ph), len(merged), self.threshold, self.autoban)

    @tasks.loop(seconds=30)
    async def _refresh_task(self):
        await self._refresh_once()

    @_refresh_task.before_loop
    async def _before(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(2)
        await self._refresh_once()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if not message.attachments or not getattr(message, "guild", None): return
        for att in message.attachments:
            if not att.content_type or not att.content_type.startswith("image"): continue
            try:
                b = await att.read()
                img = Image.open(io.BytesIO(b)).convert("RGB")
                h = str(imagehash.phash(img))
                for sig in self.db.get("phash", []):
                    if _hamming(sig, h) <= self.threshold:
                        if self.autoban:
                            try:
                                await message.author.ban(reason=f"Phishing image matched: {sig}")
                            except Exception:
                                pass
                        try:
                            from satpambot.bot.modules.discord_bot.helpers.banlog_helper import get_banlog_thread
                            th = await get_banlog_thread(message.guild)
                            emb = discord.Embed(title="Deteksi Gambar Phish", description=f"Match pHash <= {self.threshold}", color=0xF59E0B)
                            emb.add_field(name="Signature", value=sig, inline=False)
                            emb.add_field(name="Hash", value=h, inline=False)
                            emb.add_field(name="User", value=f"{message.author.mention}", inline=False)
                            if th: await th.send(embed=emb)
                        except Exception:
                            pass
                        break
            except Exception:
                continue

async def setup(bot: commands.Bot):
    await bot.add_cog(AntiImagePhishGuard(bot))
