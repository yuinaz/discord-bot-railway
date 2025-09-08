
# -*- coding: utf-8 -*-
from __future__ import annotations

import asyncio
from discord.ext import commands

PREFER_MOD_SUBSTR = "tb_shim"        # prefer our formatted shim
LOWER_PRIORITY    = ("ban_secure",)  # modules whose tb should be removed if collide

def _cmd_module(cmd: commands.Command) -> str:
    try:
        return cmd.callback.__module__ or ""
    except Exception:
        return ""

class TBPriorityFix(commands.Cog):
    """Pastikan `!tb` berasal dari tb_shim; jika `ban_secure` juga punya `tb`, nonaktifkan yang itu.
    Tidak mengubah config. Hanya manipulasi runtime command table."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._done = False

    @commands.Cog.listener()
    async def on_ready(self):
        if self._done:
            return
        await asyncio.sleep(0)
        self._fix_once()
        self._done = True

    def _fix_once(self):
        tb = self.bot.get_command("tb")
        if tb is None:
            return

        mod = _cmd_module(tb)
        if PREFER_MOD_SUBSTR in mod:
            # sudah benar: tb dari tb_shim
            return

        # Jika sumbernya dari modul lower priority -> hapus dan biarkan tb_shim yang aktif
        for low in LOWER_PRIORITY:
            if low in mod:
                self.bot.remove_command("tb")
                # Jika tb_shim sudah ter-register (tergantung urutan load), biarkan;
                # kalau belum ada, kita tidak menambah apapun (cog tb_shim akan add sendiri).
                return

async def setup(bot: commands.Bot):
    await bot.add_cog(TBPriorityFix(bot))
