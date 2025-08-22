
from __future__ import annotations
import json, os
from pathlib import Path
from datetime import datetime, timezone, timedelta
from discord.ext import commands

LOG_DIR = Path("data/mod"); LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / "ban_log.json"
MAX_ITEMS = int(os.getenv("BAN_LOG_MAX", "500"))

def _now_epoch(): return int(datetime.now(timezone.utc).timestamp())
def _wib_str(ts):
    try:
        wib = datetime.fromtimestamp(int(ts), tz=timezone.utc) + timedelta(hours=7)
        return wib.strftime("%A, %d/%m/%y")
    except Exception: return str(ts)

def _load():
    try:
        if LOG_FILE.exists():
            data = json.loads(LOG_FILE.read_text("utf-8"))
            if isinstance(data, dict) and "items" in data: data = data["items"]
            if isinstance(data, list): return data
    except Exception: pass
    return []

def _save(items):
    try: LOG_FILE.write_text(json.dumps(items[-MAX_ITEMS:], ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception: pass

class BanLogger(commands.Cog):
    def __init__(self, bot): self.bot = bot
    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        items = _load(); ts = _now_epoch()
        items.append({"type":"ban","user":getattr(user,"name","?"),"user_id":getattr(user,"id",None),"guild_id":getattr(guild,"id",None),"ts":ts,"when":_wib_str(ts)})
        _save(items)
    @commands.Cog.listener()
    async def on_member_unban(self, guild, user):
        items = _load(); ts = _now_epoch()
        items.append({"type":"unban","user":getattr(user,"name","?"),"user_id":getattr(user,"id",None),"guild_id":getattr(guild,"id",None),"ts":ts,"when":_wib_str(ts)})
        _save(items)

async def setup(bot): await bot.add_cog(BanLogger(bot))
