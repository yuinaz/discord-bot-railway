from __future__ import annotations
import discord
from discord.ext import commands
from typing import Optional, Callable, Awaitable

MOD_PERMS = ("administrator", "manage_guild", "manage_messages", "kick_members", "ban_members")

def _is_mod(member: discord.Member) -> bool:
    try:
        p = member.guild_permissions
        return any(getattr(p, name, False) for name in MOD_PERMS)
    except Exception:
        return False

class PrefixModOnly(commands.Cog):
    """
    Restriksi: prefix '!' hanya untuk moderator.
    Implementasi:
      1) Pasang global check supaya command valid berprefix '!' hanya bisa dieksekusi oleh mod.
      2) Patch bot.on_message: pesan yang diawali '!' dari non-mod DIABAIKAN lebih awal
         sehingga parser tidak jalan -> tidak ada CommandNotFound dan tidak ada error embed di channel.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._installed_check = False
        self._orig_on_message: Optional[Callable[[discord.Message], Awaitable[None]]] = getattr(bot, "on_message", None)

        # 1) Global check (untuk command yang valid)
        try:
            self.bot.add_check(self._modcheck)
            self._installed_check = True
        except Exception:
            pass  # tetap aman kalau add_check tidak tersedia

        # 2) Patch on_message agar non-mod '!' disaring sebelum process_commands()
        async def patched_on_message(message: discord.Message):
            try:
                if message and message.guild and not message.author.bot:
                    content = (getattr(message, "content", "") or "")
                    if content.startswith("!") and isinstance(message.author, discord.Member) and not _is_mod(message.author):
                        return  # swallow: jangan terus ke parser/handler lain
            except Exception:
                # kalau terjadi error saat cek, tetap teruskan ke handler asli
                pass
            if self._orig_on_message is not None:
                return await self._orig_on_message(message)  # biasanya memanggil process_commands(message)

        # pasang patch
        self.bot.on_message = patched_on_message  # type: ignore[attr-defined]

    def cog_unload(self):
        # lepas check & kembalikan on_message asli jika cog di-unload
        try:
            if self._installed_check:
                self.bot.remove_check(self._modcheck)
        except Exception:
            pass
        try:
            if self._orig_on_message is not None:
                self.bot.on_message = self._orig_on_message  # type: ignore[attr-defined]
        except Exception:
            pass

    async def _modcheck(self, ctx: commands.Context):
        pref = (ctx.prefix or "")
        if pref.startswith("!"):
            if isinstance(ctx.author, discord.Member) and not _is_mod(ctx.author):
                raise commands.CheckFailure("mod-only prefix")
        return True

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        # Unknown command '!' oleh non-mod -> diam
        if isinstance(error, commands.CommandNotFound):
            try:
                if ctx.message and ctx.message.content and ctx.message.content.startswith("!"):
                    if isinstance(ctx.author, discord.Member) and not _is_mod(ctx.author):
                        return
            except Exception:
                return
        # Gagal check mod-only -> diam
        if isinstance(error, commands.CheckFailure) and "mod-only prefix" in str(error):
            return
        # Biarkan error lain ditangani handler lain (tidak mengirim apa pun di sini)

async def setup(bot: commands.Bot):
    await bot.add_cog(PrefixModOnly(bot))
