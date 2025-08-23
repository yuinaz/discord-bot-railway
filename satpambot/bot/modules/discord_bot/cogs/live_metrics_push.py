
import os, asyncio, json, time, tempfile, logging
from typing import Dict, Any, Optional

import discord
from discord.ext import tasks, commands

log = logging.getLogger(__name__)

GUILD_ID_DEFAULT = 761163966030151701  # LeinDiscord
INTERVAL_DEFAULT_SEC = int(os.environ.get("SATPAMBOT_METRICS_INTERVAL", "60"))

def _stats_file() -> str:
    return os.environ.get("SATPAMBOT_LIVE_STATS_FILE",
                          os.path.join(tempfile.gettempdir(), "satpambot_live_stats.json"))

def _atomic_write(path: str, data: Dict[str, Any]) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    os.replace(tmp, path)

def _safe_psutil() -> Dict[str, Any]:
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory().percent
        return {"cpu": cpu, "ram": mem}
    except Exception:
        return {"cpu": 0.0, "ram": 0.0}

def _pick_primary_guild(bot: commands.Bot) -> Optional[discord.Guild]:
    gid_env = os.environ.get("SATPAMBOT_METRICS_GUILD_ID") or os.environ.get("GUILD_ID")
    gid = None
    if gid_env:
        try: gid = int(gid_env)
        except Exception: gid = None
    if gid is None:
        gid = GUILD_ID_DEFAULT
    g = bot.get_guild(gid) if gid else None
    if g: return g
    best, best_n = None, -1
    for gg in bot.guilds:
        n = getattr(gg, "member_count", 0) or 0
        if n > best_n: best, best_n = gg, n
    return best

class LiveMetricsPush(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._started = False
        self.push_loop.change_interval(seconds=INTERVAL_DEFAULT_SEC)

    @commands.Cog.listener()
    async def on_ready(self):
        if not self._started:
            self._started = True
            gids = [g.id for g in self.bot.guilds]
            log.info("[live_metrics] loop=%ss guilds=%s default_gid=%s",
                     INTERVAL_DEFAULT_SEC, gids, GUILD_ID_DEFAULT)
            self.push_loop.start()

    @tasks.loop(seconds=60.0)
    async def push_loop(self):
        await self.bot.wait_until_ready()
        g = _pick_primary_guild(self.bot)

        member_total = int(getattr(g, "member_count", 0) or 0) if g else 0

        online = 0
        try:
            if g and any(True for _m in g.members):
                online = sum(1 for m in g.members if str(getattr(m, "status", "offline")) != "offline")
        except Exception:
            online = 0

        sysm = _safe_psutil()
        latency_ms = int((getattr(self.bot, "latency", 0.0) or 0.0) * 1000)

        payload = {
            "ts": int(time.time()),
            "guild_id": g.id if g else None,
            "member_count": member_total,
            "online_count": int(online),
            "latency_ms": latency_ms,
            "cpu": float(sysm.get("cpu", 0.0)),
            "ram": float(sysm.get("ram", 0.0)),
        }

        pushed = False
        try:
            from satpambot.dashboard import live_store as _ls  # type: ignore
            for name in ("update_stats", "write_stats", "set_stats", "set", "publish_stats"):
                fn = getattr(_ls, name, None)
                if callable(fn):
                    try:
                        fn(payload)
                        pushed = True
                        break
                    except Exception as e:
                        log.debug("live_store.%s failed: %s", name, e)
            if not pushed:
                try:
                    setattr(_ls, "STATS", payload)
                    pushed = True
                except Exception:
                    pass
        except Exception as e:
            log.debug("live_store import not available: %s", e)

        if not pushed:
            try:
                tmp = _stats_file()
                with open(tmp+".tmp", "w", encoding="utf-8") as f:
                    import json as _j
                    _j.dump(payload, f, ensure_ascii=False)
                os.replace(tmp+".tmp", tmp)
                pushed = True
            except Exception as e:
                log.warning("failed writing live stats file: %s", e)

        log.debug("[live_metrics] pushed: %s", payload)

    @push_loop.before_loop
    async def before_loop(self):
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot):
    await bot.add_cog(LiveMetricsPush(bot))
