\
import asyncio, json, os, hashlib, datetime as dt
import discord
from discord.ext import commands, tasks

def _compute_phash_bytes(b: bytes) -> int:
    try:
        from satpambot.bot.utils.phash_db import compute_phash as _ph
        return _ph(b)
    except Exception:
        import PIL.Image as Image, io
        img = Image.open(io.BytesIO(b)).convert("L").resize((8,8))
        px = list(img.getdata())
        avg = sum(px)/len(px)
        bits = 0
        for i,p in enumerate(px):
            bits |= (1 if p>=avg else 0) << i
        return bits

def _load_cfg():
    # Try legacy providers first
    for mod in ("satpambot.config.compat_conf", "satpambot.config.runtime_memory"):
        try:
            m = __import__(mod, fromlist=["get_conf"])
            fn = getattr(m, "get_conf", None)
            if callable(fn):
                conf = fn()
                if isinstance(conf, dict):
                    return conf
        except Exception:
            pass
    # Fallback to runtime/local cfg; build a dict
    conf = {}
    try:
        from satpambot.config.runtime import cfg as rcfg
        keys = [
            "PHASH_DB_PATH","PHASH_INDEX_LOG_CHANNEL_ID","PHASH_INDEX_THREAD_NAMES","PHASH_INDEX_THREAD_IDS",
            "PHASH_INDEX_BACKFILL_DAYS","PHASH_INDEX_SCAN_INTERVAL","PHISH_ENFORCE_MODE","PHISH_STRONG_DISTANCE",
            "PHISH_MODERATE_DISTANCE","PHISH_MIN_LABELED_DUPLICATES","PHISH_ACTION_STRONG","PHISH_ACTION_MODERATE",
            "PHISH_DELETE_MESSAGE_DAYS","PHISH_BAN_REASON_PRESET","PHISH_BAN_REASON_SUFFIX","PHISH_MIME_SNIFF_ENABLE",
            "PHASH_INDEX_ALLOW_EXTS"
        ]
        for k in keys:
            v = rcfg(k)
            if v is not None:
                conf[k] = v
    except Exception:
        pass
    # Reasonable defaults
    conf.setdefault("PHASH_DB_PATH", "data/phash/SATPAMBOT_PHASH_DB_V1.json")
    conf.setdefault("PHASH_INDEX_LOG_CHANNEL_ID", 0)
    conf.setdefault("PHASH_INDEX_THREAD_NAMES", ["imagephising"])
    conf.setdefault("PHASH_INDEX_THREAD_IDS", [])
    conf.setdefault("PHASH_INDEX_BACKFILL_DAYS", 14)
    conf.setdefault("PHASH_INDEX_SCAN_INTERVAL", 600)
    conf.setdefault("PHASH_INDEX_ALLOW_EXTS", "png,jpg,jpeg,gif,webp")
    conf.setdefault("PHISH_ENFORCE_MODE", "always")
    conf.setdefault("PHISH_STRONG_DISTANCE", 4)
    conf.setdefault("PHISH_MODERATE_DISTANCE", 8)
    conf.setdefault("PHISH_MIN_LABELED_DUPLICATES", 2)
    conf.setdefault("PHISH_ACTION_STRONG", "ban")
    conf.setdefault("PHISH_ACTION_MODERATE", "delete")
    conf.setdefault("PHISH_DELETE_MESSAGE_DAYS", 7)
    conf.setdefault("PHISH_BAN_REASON_PRESET", "compromised")
    conf.setdefault("PHISH_BAN_REASON_SUFFIX", "Anti-Image Guard (armed)")
    conf.setdefault("PHISH_MIME_SNIFF_ENABLE", True)
    return conf
def _load_db(path):
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path,"w",encoding="utf-8") as f: json.dump([], f)
        return []
    try:
        return json.load(open(path,encoding="utf-8"))
    except Exception:
        return []

def _save_db(path, data):
    tmp = path + ".tmp"
    with open(tmp,"w",encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)

class ImagePhishRefIndexerV2(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.cfg = _load_cfg()
        self.db_path = self.cfg.get("PHASH_DB_PATH", "data/phash/SATPAMBOT_PHASH_DB_V1.json")
        self.log_ch_id = int(self.cfg.get("PHASH_INDEX_LOG_CHANNEL_ID", 0))
        self.allow_exts = set(str(self.cfg.get("PHASH_INDEX_ALLOW_EXTS","png,jpg,jpeg,gif,webp")).lower().split(","))
        self.thread_names = set([s.strip().lower() for s in self.cfg.get("PHASH_INDEX_THREAD_NAMES",[]) or []])
        self.thread_ids = [int(x) for x in str(self.cfg.get("PHASH_INDEX_THREAD_IDS","")).split(",") if x.strip().isdigit()]
        self.backfill_days = int(self.cfg.get("PHASH_INDEX_BACKFILL_DAYS", 14))
        self.scan_interval = int(self.cfg.get("PHASH_INDEX_SCAN_INTERVAL", 600))
        self._threads = []

    def _status_embed(self, added:int, scanned:int):
        e = discord.Embed(title="ImagePhish Indexer", description="Thread link → pHash DB", color=0x2ecc71)
        e.add_field(name="Added", value=str(added))
        e.add_field(name="Scanned", value=str(scanned))
        e.timestamp = discord.utils.utcnow()
        return e

    async def _find_threads(self):
        ch = self.bot.get_channel(self.log_ch_id)
        if not isinstance(ch, discord.TextChannel):
            return []
        out = []
        try:
            out.extend(ch.threads)
        except Exception:
            pass
        try:
            async for th in ch.archived_threads(limit=50):
                out.append(th)
        except Exception:
            pass
        wanted = set(self.thread_ids)
        out_ids = []
        for th in out:
            if wanted and th.id in wanted:
                out_ids.append(th)
            elif self.thread_names and str(th.name).strip().lower() in self.thread_names:
                out_ids.append(th)
        return out_ids

    async def _scan_thread(self, thread: discord.Thread, since: dt.datetime):
        added = 0
        scanned = 0
        db = _load_db(self.db_path)
        known_sha = {it.get("sha256") for it in db if "sha256" in it}
        known_msg = {it.get("message_id") for it in db if "message_id" in it}

        async for msg in thread.history(limit=None, after=since, oldest_first=True):
            scanned += 1
            if not msg.attachments:
                continue
            for att in msg.attachments:
                name = (att.filename or "").lower()
                ext = name.rsplit(".",1)[-1] if "." in name else ""
                if ext not in self.allow_exts:
                    continue
                b = await att.read(use_cached=True)
                sha = hashlib.sha256(b).hexdigest()
                if sha in known_sha or msg.id in known_msg:
                    continue
                # pHash
                ph = _compute_phash_bytes(b)
                entry = {
                    "phash": ph,
                    "sha256": sha,
                    "label": "phish",
                    "source_jump_url": msg.jump_url,
                    "message_id": msg.id,
                    "thread_id": thread.id,
                    "created_at": msg.created_at.isoformat()
                }
                db.append(entry)
                known_sha.add(sha)
                known_msg.add(msg.id)
                added += 1

        if added>0:
            _save_db(self.db_path, db)
        return added, scanned

    @tasks.loop(seconds=60)
    async def _delayed_start(self):
        self._delayed_start.cancel()
        await asyncio.sleep(5)
        await self.rebuild_index(initial=True)
        self._periodic_scan.start()

    @tasks.loop(seconds=300)
    async def _periodic_scan(self):
        try:
            since = discord.utils.utcnow() - dt.timedelta(seconds=self.scan_interval*2)
            threads = self._threads or await self._find_threads()
            self._threads = threads
            total_added = 0
            total_scanned = 0
            for th in threads:
                a,s = await self._scan_thread(th, since=since)
                total_added += a; total_scanned += s
            ch = self.bot.get_channel(self.log_ch_id)
            if ch:
                await ch.send(embed=self._status_embed(total_added, total_scanned))
        except Exception as e:
            try:
                ch = self.bot.get_channel(self.log_ch_id)
                if ch: await ch.send(f"[indexer] error: {e}")
            except Exception:
                pass

    async def rebuild_index(self, initial=False):
        threads = await self._find_threads()
        self._threads = threads
        since = discord.utils.utcnow() - dt.timedelta(days=self.backfill_days)
        total_added = 0; total_scanned = 0
        for th in threads:
            a,s = await self._scan_thread(th, since=since)
            total_added += a; total_scanned += s
        ch = self.bot.get_channel(self.log_ch_id)
        if ch:
            tag = "initial" if initial else "manual"
            e = self._status_embed(total_added, total_scanned)
            e.set_footer(text=f"backfill:{tag}")
            await ch.send(embed=e)

    @commands.Cog.listener()
    async def on_ready(self):
        self._delayed_start.start()

async def setup(bot: commands.Bot):
    await bot.add_cog(ImagePhishRefIndexerV2(bot))