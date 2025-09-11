import asyncio
import json
from discord.ext import commands, tasks
import discord

from satpambot.bot.modules.discord_bot.helpers.static_cfg import (
    PHASH_HIT_DISTANCE as HIT_DISTANCE,
    DHASH_HIT_DISTANCE as DHIT_DISTANCE,
    TILE_GRID, TILE_HIT_MIN, TILE_PHASH_DISTANCE,
)
from satpambot.bot.modules.discord_bot.helpers.img_hashing import (
    phash_hit, hex_hit, tile_match_best, phash_list_from_bytes
)

# Optional helpers (if present)
try:
    from satpambot.bot.modules.discord_bot.helpers.img_hashing import dhash_list_from_bytes
except Exception:
    dhash_list_from_bytes = None
try:
    from satpambot.bot.modules.discord_bot.helpers.img_hashing import tile_phash_list_from_bytes
except Exception:
    tile_phash_list_from_bytes = None

PHASH_DB_TITLE = "SATPAMBOT_PHASH_DB_V1"
from satpambot.bot.modules.discord_bot.helpers import static_cfg as _cfg
INBOX_NAME = getattr(_cfg, "PHISH_INBOX_THREAD", "imagephising").lower()

def _extract_hashes_from_content(s: str):
    if not s:
        return [], [], []
    i, j = s.find("{"), s.rfind("}")
    if i == -1 or j == -1 or j <= i:
        return [], [], []
    try:
        obj = json.loads(s[i:j+1])
        P = [str(x).strip() for x in (obj.get("phash", []) or []) if str(x).strip()]
        D = [str(x).strip() for x in (obj.get("dhash", []) or []) if str(x).strip()]
        T = [str(x).strip() for x in (obj.get("tphash", []) or []) if str(x).strip()]
        return P, D, T
    except Exception:
        return [], [], []

class AntiImagePhashRuntime(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._phash_set = set()
        self._dhash_set = set()
        self._tile_set  = set()
        self._bootstrap.start()

    def cog_unload(self):
        try: self._bootstrap.cancel()
        except Exception: pass

    def _ensure_sets(self):
        if not hasattr(self, "_phash_set"): self._phash_set = set()
        if not hasattr(self, "_dhash_set"): self._dhash_set = set()
        if not hasattr(self, "_tile_set"):  self._tile_set  = set()

    @tasks.loop(count=1)
    async def _bootstrap(self):
        try:
            await self.bot.wait_until_ready()
            await asyncio.sleep(4)
            await self._reload_from_db_all_guilds()
        except Exception:
            pass

    async def _reload_from_db_all_guilds(self):
        for g in list(self.bot.guilds):
            try:
                t = next((th for th in g.threads if (th.name or '').lower() == INBOX_NAME), None)
                parent = getattr(t, "parent", None)
                if not parent:
                    continue
                db_msg = None
                async for m in parent.history(limit=50):
                    if m.author.id == self.bot.user.id and PHASH_DB_TITLE in (m.content or ""):
                        db_msg = m; break
                if not db_msg:
                    continue
                P, D, T = _extract_hashes_from_content(db_msg.content or "")
                self._ensure_sets()
                self._phash_set = set(P)
                self._dhash_set = set(D)
                self._tile_set  = set(T)
            except Exception:
                continue

    @commands.Cog.listener("on_message_edit")
    async def _on_db_edit_reload(self, before: discord.Message, after: discord.Message):
        try:
            if after and after.author and after.author.id == self.bot.user.id and PHASH_DB_TITLE in (after.content or ""):
                P, D, T = _extract_hashes_from_content(after.content or "")
                self._ensure_sets()
                self._phash_set = set(P)
                self._dhash_set = set(D)
                self._tile_set  = set(T)
        except Exception:
            pass

    @commands.Cog.listener("on_message")
    async def on_message(self, message: discord.Message):
        try:
            if getattr(message.author, "bot", False):
                return
            if not message.attachments:
                return

            # Read first image (runtime check is lightweight)
            raw = None
            for att in message.attachments:
                n = (att.filename or "").lower()
                if n.endswith((".png",".jpg",".jpeg",".webp",".gif",".bmp",".tif",".tiff",".heic",".heif")):
                    raw = await att.read(); break
            if not raw:
                return

            all_hashes = phash_list_from_bytes(raw, max_frames=4, augment=False, augment_per_frame=0)
            all_dhashes = dhash_list_from_bytes(raw, max_frames=4, augment=False, augment_per_frame=0) if dhash_list_from_bytes else []
            all_tiles = tile_phash_list_from_bytes(raw, grid=TILE_GRID, max_frames=2, augment=False, augment_per_frame=0) if tile_phash_list_from_bytes else []

            self._ensure_sets()

            hitp = phash_hit(all_hashes, self._phash_set, max_distance=HIT_DISTANCE) if all_hashes and self._phash_set else None
            if hitp: return

            hitd = hex_hit(all_dhashes, self._dhash_set, max_distance=DHIT_DISTANCE) if all_dhashes and self._dhash_set else None
            if hitd: return

            # Optional tile — we only compute above if helper exists
            if all_tiles and self._tile_set:
                # will return list of matches; treat presence as hit
                tile_hits = tile_match_best(all_tiles, self._tile_set, grid=TILE_GRID, min_tiles=TILE_HIT_MIN, per_tile_max_distance=TILE_PHASH_DISTANCE)
                if tile_hits:
                    return
        except Exception:
            return
