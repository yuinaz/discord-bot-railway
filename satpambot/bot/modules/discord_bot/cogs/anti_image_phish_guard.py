from __future__ import annotations
import discord, io, logging, os, json
from discord.ext import commands
from PIL import Image
import imagehash

log = logging.getLogger(__name__)

PHISH_IMG_DB = os.getenv("PHISH_IMG_DB", "data/phish_phash.json")
PHISH_CONFIG_PATH = os.getenv("PHISH_CONFIG_PATH", "data/phish_config.json")

def _load_json(path:str)->dict:
    try:
        with open(path, "r", encoding="utf-8") as f: return json.load(f)
    except Exception:
        return {}

def _save_json(path:str, data:dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=2)

def _hamming(a:str,b:str)->int:
    try:
        return bin(int(a,16) ^ int(b,16)).count("1")
    except Exception:
        return 999

class AntiImagePhishGuard(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = _load_json(PHISH_IMG_DB)
        self.cfg = _load_json(PHISH_CONFIG_PATH)
        self.threshold = int(self.cfg.get("threshold", 8))
        self.autoban = bool(self.cfg.get("autoban", False))
        log.info("[phish] load phash=%s threshold=%s autoban=%s", len(self.db.get("phash",[])), self.threshold, self.autoban)

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
                        try:
                            await message.delete()
                        except Exception:
                            pass
                        await self._log_detect(message, sig, h)
                        if self.autoban:
                            try:
                                await message.guild.ban(message.author, reason="Phish image signature match")
                            except Exception:
                                pass
                        return
            except Exception as e:
                log.debug("[phish] error reading attachment: %s", e)

    async def _log_detect(self, message: discord.Message, sig: str, h: str):
        # Simple log to banlog thread
        try:
            from satpambot.bot.modules.discord_bot.helpers.banlog_helper import get_banlog_thread
            th = await get_banlog_thread(message.guild)
            emb = discord.Embed(title="Deteksi Gambar Phishing", description=f"Match pHash <= {self.threshold}", color=0xF59E0B)
            emb.add_field(name="Signature", value=sig, inline=False)
            emb.add_field(name="Hash", value=h, inline=False)
            emb.add_field(name="User", value=f"{message.author.mention}", inline=False)
            if th:
                await th.send(embed=emb)
        except Exception:
            pass

async def setup(bot: commands.Bot):
    await bot.add_cog(AntiImagePhishGuard(bot))
