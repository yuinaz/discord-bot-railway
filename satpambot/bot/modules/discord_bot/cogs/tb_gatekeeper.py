
# -*- coding: utf-8 -*-
from __future__ import annotations

import asyncio
from typing import Optional, Tuple
from discord.ext import commands

CANDIDATES: Tuple[str, ...] = ("tempban", "tban", "ban")

def _is_shim(cmd: commands.Command) -> bool:
    try:
        mod = cmd.callback.__module__
        return ("tb_shim" in mod)
    except Exception:
        return False

class TBGatekeeperPreferShim(commands.Cog):
    """Finalizer `tb`:
    - Jika sudah ada `tb` dari shim (module mengandung 'tb_shim'), BIARKAN (prefer simulasi).
    - Jika tidak ada, dan ada target nyata, pasang alias tb -> target (tempban/tban/ban).
    - Jika tetap tidak ada target, pasang shim sangat ringan (pesan teks) supaya tidak CommandNotFound.
    Tidak mengubah config, hanya memastikan runtime konsisten.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._applied = False

    @commands.Cog.listener()
    async def on_ready(self):
        if self._applied:
            return
        await asyncio.sleep(0)
        await self._apply_once()
        self._applied = True

    async def _apply_once(self):
        existing = self.bot.get_command("tb")
        if existing and _is_shim(existing):
            # Sudah ada `tb` dari shim -> hormati, jangan override
            return

        target = self._choose_target()
        if target:
            # Replace tb jadi alias ke target
            self.bot.remove_command("tb")

            async def _tb_alias(ctx: commands.Context, *args):
                cmd = self.bot.get_command(target)
                if cmd is None:
                    await ctx.send("⚠️ Target 'tb' tidak tersedia. Coba lagi.", delete_after=8)
                    return
                return await ctx.invoke(cmd, *args)

            alias_cmd = commands.Command(_tb_alias, name="tb", help=f"Alias legacy: tb -> {target}")
            self.bot.add_command(alias_cmd)
        else:
            # Pasang shim minimal (text) agar tak error
            self.bot.remove_command("tb")

            async def _tb_shim_text(ctx: commands.Context, *args):
                await ctx.send("ℹ️ Simulasi tb: modul ban belum aktif.")

            self.bot.add_command(commands.Command(_tb_shim_text, name="tb", help="Simulasi tb (ringan)"))

    def _choose_target(self) -> Optional[str]:
        for name in CANDIDATES:
            if self.bot.get_command(name):
                return name
        return None

async def setup(bot: commands.Bot):
    await bot.add_cog(TBGatekeeperPreferShim(bot))
