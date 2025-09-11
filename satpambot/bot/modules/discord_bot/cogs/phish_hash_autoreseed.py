import asyncio
import json
import discord
from discord.ext import commands, tasks
from discord import AllowedMentions

from satpambot.bot.modules.discord_bot.helpers import img_hashing, static_cfg

PHASH_DB_TITLE = "SATPAMBOT_PHASH_DB_V1"
IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff", ".heic", ".heif")

# Respect existing toggles (do not change config file)
NOTIFY_THREAD = getattr(static_cfg, "PHISH_NOTIFY_THREAD", False)
LOG_TTL_SECONDS = int(getattr(static_cfg, "PHISH_LOG_TTL", 0))  # 0 = keep forever
INBOX_NAME = getattr(static_cfg, "PHISH_INBOX_THREAD", "imagephising").lower()

# Limits to be gentle on Free plan
LIMIT_MSGS = int(getattr(static_cfg, "PHISH_AUTO_RESEED_LIMIT", 2000))  # default 2000 msgs
SLEEP_EVERY = 25
SLEEP_SECONDS = 1

def _render_db(phashes, dhashes=None, tiles=None):
    data = {"phash": phashes}
    if dhashes: data["dhash"] = dhashes
    if tiles:   data["tphash"] = tiles
    return f"{PHASH_DB_TITLE}\\n```json\\n{json.dumps(data, ensure_ascii=False)}\\n```"

def _extract_hashes_from_json_msg(msg: discord.Message):
    if not msg or not msg.content:
        return [], [], []
    s = msg.content
    i, j = s.find("{"), s.rfind("}")
    if i != -1 and j != -1 and j > i:
        try:
            obj = json.loads(s[i:j+1])
            arr_p = obj.get("phash", []) or []
            arr_d = obj.get("dhash", []) or []
            arr_t = obj.get("tphash", []) or []
            P = [str(x).strip() for x in arr_p if str(x).strip()]
            D = [str(x).strip() for x in arr_d if str(x).strip()]
            T = [str(x).strip() for x in arr_t if str(x).strip()]
            return P, D, T
        except Exception:
            return [], [], []
    return [], [], []

class PhishHashAutoReseed(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._ran_guilds = set()
        # start background loop
        self.auto_task.start()

    def cog_unload(self):
        try:
            self.auto_task.cancel()
        except Exception:
            pass

    @tasks.loop(count=1)
    async def auto_task(self):
        # wait until bot is ready
        await self.bot.wait_until_ready()
        # small delay to let cache populate
        await asyncio.sleep(3)
        # iterate guilds
        for g in list(self.bot.guilds):
            if g.id in self._ran_guilds:
                continue
            try:
                await self._process_guild(g)
                self._ran_guilds.add(g.id)
            except Exception:
                continue

    async def _process_guild(self, guild: discord.Guild):
        # find active thread named INBOX_NAME
        target_thread = None
        try:
            for th in guild.threads:  # active threads
                if (th.name or "").lower() == INBOX_NAME:
                    target_thread = th
                    break
        except Exception:
            target_thread = None

        if not target_thread:
            return  # skip silently if not found or archived

        parent = target_thread.parent if hasattr(target_thread, "parent") else None
        if not parent:
            return

        # if DB already looks complete (has dhash & tphash), skip heavy scan
        db_msg = None
        try:
            async for m in parent.history(limit=50):
                if m.author.id == self.bot.user.id and PHASH_DB_TITLE in (m.content or ""):
                    db_msg = m
                    break
        except Exception:
            db_msg = None

        if db_msg:
            P, D, T = _extract_hashes_from_json_msg(db_msg)
            if (len(P) >= 1 and len(D) >= 1 and len(T) >= 1):
                return  # already contains all fields, skip

        # scan thread history (oldest_first)
        all_p, all_d, all_t = [], [], []
        scanned_msgs = 0
        scanned_atts = 0
        try:
            async for m in target_thread.history(limit=LIMIT_MSGS, oldest_first=True):
                scanned_msgs += 1
                if not m.attachments:
                    continue
                for att in m.attachments:
                    name = (att.filename or "").lower()
                    if not any(name.endswith(ext) for ext in IMAGE_EXTS):
                        continue
                    try:
                        raw = await att.read()
                    except Exception:
                        continue
                    if not raw:
                        continue
                    scanned_atts += 1

                    hs = img_hashing.phash_list_from_bytes(
                        raw,
                        max_frames=getattr(static_cfg, "PHASH_MAX_FRAMES", 6),
                        augment=getattr(static_cfg, "PHASH_AUGMENT_REGISTER", True),
                        augment_per_frame=getattr(static_cfg, "PHASH_AUGMENT_PER_FRAME", 5),
                    )
                    if hs: all_p.extend(hs)

                    dh_func = getattr(img_hashing, "dhash_list_from_bytes", None)
                    if dh_func:
                        ds = dh_func(
                            raw,
                            max_frames=getattr(static_cfg, "PHASH_MAX_FRAMES", 6),
                            augment=getattr(static_cfg, "PHASH_AUGMENT_REGISTER", True),
                            augment_per_frame=getattr(static_cfg, "PHASH_AUGMENT_PER_FRAME", 5),
                        )
                        if ds: all_d.extend(ds)

                    t_func = getattr(img_hashing, "tile_phash_list_from_bytes", None)
                    if t_func:
                        ts = t_func(
                            raw,
                            grid=getattr(static_cfg, "TILE_GRID", 3),
                            max_frames=getattr(static_cfg, "PHASH_MAX_FRAMES", 4),
                            augment=getattr(static_cfg, "PHASH_AUGMENT_REGISTER", True),
                            augment_per_frame=3,
                        )
                        if ts: all_t.extend(ts)

                    if (scanned_atts % SLEEP_EVERY) == 0:
                        await asyncio.sleep(SLEEP_SECONDS)

        except Exception:
            return  # silent fail to avoid breaking bot

        if not (all_p or all_d or all_t):
            return

        # Merge with existing DB
        existing_p, existing_d, existing_t = ([], [], [])
        if db_msg:
            existing_p, existing_d, existing_t = _extract_hashes_from_json_msg(db_msg)

        sp, sd, st = set(existing_p), set(existing_d), set(existing_t)
        for h in all_p:
            if h not in sp:
                existing_p.append(h); sp.add(h)
        for h in all_d:
            if h not in sd:
                existing_d.append(h); sd.add(h)
        for t in all_t:
            if t not in st:
                existing_t.append(t); st.add(t)

        content = _render_db(existing_p, existing_d, existing_t)

        if db_msg:
            try:
                await db_msg.edit(content=content)
            except Exception:
                pass
        else:
            try:
                db_msg = await parent.send(content)
            except Exception:
                db_msg = None

        # Optional summary log
        try:
            emb = discord.Embed(
                title="Auto reseed selesai",
                description=f"Thread: {target_thread.mention}\nScanned: {scanned_msgs} msgs / {scanned_atts} attachments",
                colour=0x00B894,
            )
            emb.add_field(name="Total pHash", value=str(len(existing_p)), inline=True)
            emb.add_field(name="Total dHash", value=str(len(existing_d)), inline=True)
            if parent:
                m = await parent.send(embed=emb, allowed_mentions=AllowedMentions.none())
                if LOG_TTL_SECONDS > 0:
                    try:
                        asyncio.create_task(self._autodel(m, LOG_TTL_SECONDS))
                    except Exception:
                        pass
        except Exception:
            pass

    async def _autodel(self, msg: discord.Message, delay: int):
        try:
            await asyncio.sleep(delay)
            await msg.delete()
        except Exception:
            pass

    @auto_task.before_loop
    async def _before(self):
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot):
    await bot.add_cog(PhishHashAutoReseed(bot))

def legacy_setup(bot: commands.Bot):
    bot.add_cog(PhishHashAutoReseed(bot))
