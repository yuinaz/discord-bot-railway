# learning_passive_observer.py
from discord.ext import commands, tasks
import discord, logging, json, time
from pathlib import Path
log = logging.getLogger(__name__)
DATA_FILE = Path("data/neuro-lite/learn_progress_junior.json")
BAN_LOG_FILE = Path("data/neuro-lite/ban_events.jsonl")
BLOCK_CHANNEL_IDS = {763793237394718744}
MSG_MIN_CHARS = 10
POINTS_PER_MSG = 1
POINTS_PER_100_CHARS = 1
HOUR_TARGET_POINTS = 10_000  # 1 point = 0.01%%
BOT_BAN_POINTS = 100
MOD_ADMIN_BAN_POINTS = 25
LEVEL_THRESHOLDS = [(0,"TK"),(1_000,"SD"),(5_000,"SMP"),(15_000,"SMA"),(30_000,"Diploma"),(60_000,"Sarjana"),(120_000,"Master"),(240_000,"Gubernur")]
def _level_from_xp(xp: int):
    name = LEVEL_THRESHOLDS[0][1]
    for t, n in LEVEL_THRESHOLDS:
        if xp >= t: name = n
        else: break
    return name
def _safe_load(p: Path):
    try:
        if p.exists():
            with p.open("r", encoding="utf-8") as f: return json.load(f)
    except Exception as e: log.warning("[passive-learning] load fail: %s", e)
    return {"xp_total":0,"hour_progress_pct":0,"hour_points":0,"hour_start":int(time.time()),"level":"TK"}
def _safe_dump(p: Path, data: dict):
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=2)
        tmp.replace(p)
    except Exception as e: log.warning("[passive-learning] save fail: %s", e)
def _append_jsonl(p: Path, obj: dict):
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a", encoding="utf-8") as f: f.write(json.dumps(obj, ensure_ascii=False) + "\n")
    except Exception as e: log.warning("[passive-learning] append jsonl fail: %s", e)
def _is_blocked_channel(ch):
    try: return getattr(ch, "id", None) in BLOCK_CHANNEL_IDS
    except Exception: return False
class PassiveLearningObserver(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.data = _safe_load(DATA_FILE)
        self.hour = time.gmtime().tm_hour
        self._ticker.start()
        log.info("[passive-learning] observer ready (slow-rate); file=%s level=%s xp=%s target=%s pts/hr",
                 DATA_FILE, self.data.get("level"), self.data.get("xp_total"), HOUR_TARGET_POINTS)
    def cog_unload(self):
        try: self._ticker.cancel()
        except Exception: pass
    def _add_points(self, pts: int):
        self.data["hour_points"] = int(self.data.get("hour_points", 0) + max(0, int(pts)))
        self.data["hour_progress_pct"] = min(100, int((self.data["hour_points"] / max(1, HOUR_TARGET_POINTS)) * 100))
    def _add_points_from_msg(self, msg: discord.Message):
        if getattr(msg.author, "bot", False): return
        if _is_blocked_channel(msg.channel): return
        content = msg.content or ""
        if len(content) < MSG_MIN_CHARS: return
        pts = POINTS_PER_MSG + (len(content) // 100) * POINTS_PER_100_CHARS
        self._add_points(pts)
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        self._add_points_from_msg(message)
    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        self._add_points_from_msg(after)
    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User):
        actor = None
        try:
            async for entry in guild.audit_logs(limit=6, action=discord.AuditLogAction.ban):
                if entry.target.id == user.id: actor = entry.user; break
        except Exception as e:
            log.debug("[passive-learning] audit log fetch fail: %s", e)
        actor_id = getattr(actor, "id", None) if actor else None
        points = BOT_BAN_POINTS if (guild.me and actor_id == guild.me.id) else MOD_ADMIN_BAN_POINTS
        self._add_points(points)
        _append_jsonl(BAN_LOG_FILE, {"ts": int(time.time()), "guild_id": guild.id, "user_banned_id": user.id, "by_id": actor_id, "points": points})
        log.info("[passive-learning] ban bonus %+d pts (user=%s by=%s)", points, user.id, actor_id)
    @tasks.loop(seconds=10)
    async def _ticker(self):
        now = time.gmtime()
        if now.tm_hour != self.hour:
            gained = int(self.data.get("hour_points", 0))
            self.data["xp_total"] = int(self.data.get("xp_total", 0) + gained)
            self.data["hour_points"] = 0
            self.data["hour_progress_pct"] = 0
            self.data["hour_start"] = int(time.time())
            self.data["level"] = _level_from_xp(self.data["xp_total"])
            self.hour = now.tm_hour
            log.info("[passive-learning] +%s XP -> total=%s level=%s", gained, self.data["xp_total"], self.data["level"])
        _safe_dump(DATA_FILE, self.data)
async def setup(bot: commands.Bot):
    await bot.add_cog(PassiveLearningObserver(bot))