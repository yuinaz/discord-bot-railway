# satpambot/bot/modules/discord_bot/cogs/hot_env_reload.py
from discord.ext import tasks, commands
import asyncio, importlib, logging, os, time

log = logging.getLogger(__name__)

def _read_env(path: str) -> dict:
    env = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                s = line.strip()
                if not s or s.startswith("#"):
                    continue
                if "=" in s:
                    k, v = s.split("=", 1)
                    env[k.strip()] = v.strip()
    except FileNotFoundError:
        pass
    return env

async def _call_hook_if_any(module, bot, new_env):
    hook = getattr(module, "on_env_reload", None)
    if hook:
        try:
            if asyncio.iscoroutinefunction(hook):
                await hook(bot, new_env)
            else:
                hook(bot, new_env)
        except Exception as e:
            log.warning("[hotenv] hook %s failed: %s", getattr(module, "__name__", module), e)

class HotEnvReload(commands.Cog):
    """Pantau file ENV dan apply perubahan TANPA memutus koneksi bot.
    - Update os.environ saat file berubah
    - Reload semua cogs (agar baca ENV baru di __init__/setup)
    - (Opsional) panggil hook on_env_reload(bot, env) jika didefinisikan di cog
    """
    def __init__(self, bot: commands.Bot, env_path: str, interval: float = 2.0):
        self.bot = bot
        self.env_path = env_path
        self.interval = interval
        self._last_mtime = os.path.getmtime(env_path) if os.path.exists(env_path) else 0.0
        self._task = self._watcher.start()

    def cog_unload(self):
        try:
            self._task.cancel()
        except Exception:
            pass

    @tasks.loop(seconds=2.0)
    async def _watcher(self):
        # Sesuaikan interval dari ENV bila berubah
        try:
            iv = float(os.getenv("HOTENV_INTERVAL_SECONDS", self.interval))
        except Exception:
            iv = self.interval
        if self._watcher.seconds != iv:
            self._watcher.change_interval(seconds=iv)

        try:
            cur = os.path.getmtime(self.env_path) if os.path.exists(self.env_path) else 0.0
            if cur != self._last_mtime:
                self._last_mtime = cur
                new_env = _read_env(self.env_path)
                os.environ.update(new_env)
                log.info("[hotenv] detected change on %s; reloading all cogs...", self.env_path)

                # Panggil hook dulu (jika ada)
                for ext in list(self.bot.extensions.keys()):
                    if ext.startswith("satpambot.bot.modules.discord_bot.cogs."):
                        try:
                            mod = importlib.import_module(ext)
                            await _call_hook_if_any(mod, self.bot, new_env)
                        except Exception as e:
                            log.warning("[hotenv] pre-reload hook failed on %s: %s", ext, e)

                # Reload seluruh cogs (tanpa putus koneksi ke Discord)
                for ext in list(self.bot.extensions.keys()):
                    if ext.startswith("satpambot.bot.modules.discord_bot.cogs."):
                        try:
                            # reload_extension adalah operasi sinkron di discord.py
                            self.bot.reload_extension(ext)
                            log.info("[hotenv] reloaded %s", ext)
                        except Exception as e:
                            log.warning("[hotenv] reload failed on %s: %s", ext, e)

        except Exception as e:
            log.warning("[hotenv] watcher error: %s", e)

async def setup(bot: commands.Bot):
    enabled = os.getenv("HOTENV_ENABLED", "1") != "0"
    if not enabled:
        log.info("[hotenv] disabled by HOTENV_ENABLED=0")
        return
    env_path = os.getenv("SATPAMBOT_ENV") or os.getenv("ENV_FILE") or "SatpamBot.env"
    try:
        iv = float(os.getenv("HOTENV_INTERVAL_SECONDS", "2"))
    except Exception:
        iv = 2.0
    await bot.add_cog(HotEnvReload(bot, env_path, interval=iv))
    log.info("[hotenv] running (env=%s, interval=%ss)", env_path, iv)