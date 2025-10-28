
# a21_curriculum_autoload.py
# Ensures a20_curriculum_tk_sd is loaded, shortens first loop interval, and writes first tick.

from discord.ext import commands
import json
import logging
import asyncio
async def awaitable_safe_int(val, default=0):
    if asyncio.iscoroutine(val):
        val = await val
    if isinstance(val, (int, float)): return int(val)
    s = str(val or "").strip()
    try: return int(float(s))
    except Exception: return default

log = logging.getLogger(__name__)

class CurriculumAutoload(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _first_tick(self):
        try:
            from satpambot.bot.modules.discord_bot.cogs import a20_curriculum_tk_sd as c
        except Exception as e:
            log.warning("[curriculum_autoload] a20 not importable: %r", e)
            return
        try:
            cfg = c._load_cfg()
            tz = int(cfg.get("tz_offset_minutes", 420))
            now = c._now_local(tz)
            day_key = now.strftime("%Y-%m-%d")
            week_key = f"{now.isocalendar().year}-W{now.isocalendar().week:02d}"
            month_key = now.strftime("%Y-%m")
            try:
                obj = json.loads(c.PROGRESS_FILE.read_text(encoding="utf-8"))
            except Exception:
                obj = {"xp_total": 0, "created_at": day_key, "today": "", "daily": {}, "weekly": {}, "monthly": {}}
            xp = c._probe_total_xp_runtime(getattr(self, "bot", None)) or c._probe_total_xp_module()
            obj["xp_total"] = max(await awaitable_safe_int(obj.get("xp_total", 0), 0), await awaitable_safe_int(xp, 0))
            obj["today"] = day_key
            obj["daily"][day_key] = obj["xp_total"]
            obj["weekly"][week_key] = obj["xp_total"]
            obj["monthly"][month_key] = obj["xp_total"]
            c._ensure_dir(c.PROGRESS_FILE)
            c.PROGRESS_FILE.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
            log.info("[curriculum_autoload] first tick wrote progress.json (today=%s, xp=%s)", day_key, obj["xp_total"])
        except Exception as e:
            log.warning("[curriculum_autoload] first tick failed: %r", e)

    @commands.Cog.listener()
    async def on_ready(self):
        modname = "satpambot.bot.modules.discord_bot.cogs.a20_curriculum_tk_sd"
        try:
            if "CurriculumTKSD" not in self.bot.cogs:
                try:
                    await self.bot.load_extension(modname)
                except Exception:
                    from satpambot.bot.modules.discord_bot.cogs.a20_curriculum_tk_sd import CurriculumTKSD
                    try:
                        await self.bot.add_cog(CurriculumTKSD(self.bot))
                    except Exception as e:
                        log.warning("[curriculum_autoload] add_cog failed: %r", e)
            cog = self.bot.get_cog("CurriculumTKSD")
            if cog and getattr(cog, "_loop", None):
                try:
                    cog._loop.change_interval(minutes=2)
                    log.info("[curriculum_autoload] changed loop interval to 2 minutes for warmup")
                except Exception:
                    pass
            await self._first_tick()
        except Exception as e:
            log.warning("[curriculum_autoload] on_ready failed: %r", e)
async def setup(bot):
    await bot.add_cog(CurriculumAutoload(bot))