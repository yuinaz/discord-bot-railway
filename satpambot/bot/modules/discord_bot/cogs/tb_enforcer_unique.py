import asyncio
import logging
from discord.ext import commands

log = logging.getLogger(__name__)

def _origin_module(cmd) -> str:
    return getattr(getattr(cmd, "callback", None), "__module__", "") or ""

class TBEnforcerUnique(commands.Cog):
    """Hard guarantee: keep exactly ONE prefix command named `tb`, preferring tb_shim.
    Tidak menyentuh config, hanya memastikan mapping `bot.get_command("tb")` menunjuk ke
    command dari `tb_shim` bila ada, sehingga tidak dobel/triple.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Coba jadwalkan saat event loop sudah jalan (smoke menjalankan loop, import murni mungkin belum).
        try:
            asyncio.get_running_loop()
            self._task = asyncio.create_task(self._ensure_unique_later())
        except RuntimeError:
            self._task = None
        self._ready_once = False

    def cog_unload(self) -> None:
        t = getattr(self, "_task", None)
        if t:
            t.cancel()

    @commands.Cog.listener()
    async def on_ready(self):
        # Fallback kalau __init__ tidak berhasil menjadwalkan task (karena loop belum jalan).
        if self._ready_once:
            return
        self._ready_once = True
        await self._ensure_unique_once()

    async def _ensure_unique_later(self) -> None:
        # tunggu cogs lain register command (maks 10 detik)
        for _ in range(100):
            if await self._ensure_unique_once():
                return
            await asyncio.sleep(0.1)
        await self._ensure_unique_once()

    async def _ensure_unique_once(self) -> bool:
        # Kumpulkan semua definisi 'tb' dari cogs yang sudah terdaftar.
        tb_cmds = []
        for cog in list(self.bot.cogs.values()):
            for cmd in getattr(cog, "get_commands", lambda: [])():
                if cmd.name == "tb":
                    tb_cmds.append(cmd)

        if not tb_cmds:
            return False

        # Pilih yang dari tb_shim kalau ada.
        preferred = None
        for cmd in tb_cmds:
            if _origin_module(cmd).endswith(".tb_shim"):
                preferred = cmd
                break
        preferred = preferred or tb_cmds[0]

        active = self.bot.get_command("tb")
        if active is preferred:
            return True

        # Ganti mapping ke yang preferred.
        try:
            if active is not None:
                self.bot.remove_command("tb")
        except Exception:
            pass
        try:
            self.bot.add_command(preferred)
            log.info("[tb_enforcer_unique] mapped tb -> %s", _origin_module(preferred))
            return True
        except Exception as e:
            log.warning("[tb_enforcer_unique] failed to register preferred tb: %s", e)
            return False

async def setup(bot: commands.Bot):
    await bot.add_cog(TBEnforcerUnique(bot))
