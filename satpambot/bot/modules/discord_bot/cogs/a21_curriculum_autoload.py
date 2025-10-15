# a21_curriculum_autoload.py (patched to also load senior curriculum if available)
import json
import logging
from discord.ext import commands

log = logging.getLogger(__name__)

class CurriculumAutoload(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _first_tick(self):
        try:
            from satpambot.bot.modules.discord_bot.cogs import a20_curriculum_tk_sd as c
            from datetime import datetime, timezone, timedelta
            from pathlib import Path
            DATA_DIR = getattr(c, "DATA_DIR", None)
            if not DATA_DIR: return
            PROGRESS_FILE = getattr(c, "PROGRESS_FILE")
            tz = int(getattr(c, "DEFAULT_CFG", {}).get("tz_offset_minutes", 420))
            def _now_local(): return datetime.now(timezone.utc) + timedelta(minutes=tz)
            day_key = _now_local().strftime("%Y-%m-%d")
            week_key = _now_local().strftime("%Y-W%W")
            month_key = _now_local().strftime("%Y-%m")
            obj = {"xp_total": 0, "today": day_key, "daily": {}, "weekly": {}, "monthly": {}}
            xp = c._probe_total_xp_runtime(getattr(self, "bot", None)) or c._probe_total_xp_module()
            obj["xp_total"] = max(int(obj.get("xp_total", 0)), int(xp))
            obj["today"] = day_key
            obj["daily"][day_key] = obj["xp_total"]
            obj["weekly"][week_key] = obj["xp_total"]
            obj["monthly"][month_key] = obj["xp_total"]
            Path(PROGRESS_FILE).parent.mkdir(parents=True, exist_ok=True)
            Path(PROGRESS_FILE).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
            log.info("[curriculum_autoload] first tick wrote progress.json (today=%s, xp=%s)", day_key, obj["xp_total"])
        except Exception as e:
            log.warning("[curriculum_autoload] first tick failed: %r", e)

    async def _ensure_loaded(self, modname: str, cogname: str):
        try:
            if cogname not in self.bot.cogs:
                try:
                    await self.bot.load_extension(modname)
                except Exception:
                    mod = __import__(modname, fromlist=['*'])
                    for attr in dir(mod):
                        if attr.lower() == cogname.lower():
                            klass = getattr(mod, attr)
                            await self.bot.add_cog(klass(self.bot))
                            break
            return True
        except Exception as e:
            log.warning("[curriculum_autoload] ensure_loaded(%s) failed: %r", modname, e)
            return False

    @commands.Cog.listener()
    async def on_ready(self):
        await self._ensure_loaded("satpambot.bot.modules.discord_bot.cogs.a20_curriculum_tk_sd", "CurriculumTKSD")
        await self._ensure_loaded("satpambot.bot.modules.discord_bot.cogs.learning_curriculum_senior", "SeniorLearningPolicy")
        cog = self.bot.get_cog("CurriculumTKSD")
        if cog and getattr(cog, "_loop", None):
            try:
                cog._loop.change_interval(minutes=2)
                log.info("[curriculum_autoload] changed loop interval to 2 minutes for warmup")
            except Exception:
                pass
        await self._first_tick()

async def setup(bot):
    await bot.add_cog(CurriculumAutoload(bot))