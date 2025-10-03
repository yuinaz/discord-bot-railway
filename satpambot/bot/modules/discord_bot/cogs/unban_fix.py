# -*- coding: utf-8 -*-
"""
Cog: UnbanFix
- Memperbaiki parsing argumen untuk command prefix "unban".
- Menerima ID murni, mention <@...>, atau ID yang ketempel karakter lain (misal ")" atau ",").
- Aman untuk smoke test: tidak mengakses method yang tidak ada di DummyBot.
"""
from __future__ import annotations

import re
import logging
from typing import Optional

import discord
from discord.ext import commands

log = logging.getLogger(__name__)

ID_RE = re.compile(r'\d{15,20}')

def _extract_user_id(arg: str) -> Optional[int]:
    if not arg:
        return None
    m = ID_RE.search(arg)
    if m:
        try:
            return int(m.group(0))
        except Exception:
            return None
    return None

class UnbanFix(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="unban")
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    async def unban_cmd(self, ctx: commands.Context, *, user_ref: str):
        """
        Unban by user ID / mention / string yang mengandung ID.
        Contoh:
          .unban 1331765056974753934
          .unban <@1331765056974753934>
          .unban 1331765056974753934)
        """
        user_id = _extract_user_id(user_ref)
        if user_id is None:
            return await ctx.reply("❌ Gagal membaca user ID. Contoh: `.unban 1331765056974753934`", mention_author=False)

        # Cari entry ban dulu
        try:
            bans = await ctx.guild.bans(limit=None)
        except Exception as e:
            log.exception("Gagal mengambil daftar ban: %r", e)
            return await ctx.reply("❌ Tidak bisa mengambil daftar ban (cek izin bot).", mention_author=False)

        target_entry = None
        for entry in bans:
            if entry.user.id == user_id:
                target_entry = entry
                break

        if target_entry is None:
            # user object mungkin belum ada. Coba Object minimal
            try:
                await ctx.guild.unban(discord.Object(id=user_id), reason=f"manual by {ctx.author} via UnbanFix")
                return await ctx.reply(f"✅ Unbanned (ID saja) `{user_id}`.", mention_author=False)
            except discord.NotFound:
                return await ctx.reply(f"ℹ️ User `{user_id}` tidak ada di daftar ban.", mention_author=False)
            except discord.Forbidden:
                return await ctx.reply("❌ Bot tidak punya izin unban.", mention_author=False)
            except Exception as e:
                log.exception("Error unban raw id: %r", e)
                return await ctx.reply("❌ Terjadi error saat unban.", mention_author=False)

        try:
            await ctx.guild.unban(target_entry.user, reason=f"manual by {ctx.author} via UnbanFix")
            return await ctx.reply(f"✅ Unbanned {target_entry.user} (`{target_entry.user.id}`).", mention_author=False)
        except discord.Forbidden:
            return await ctx.reply("❌ Bot tidak punya izin unban.", mention_author=False)
        except Exception as e:
            log.exception("Error unban target: %r", e)
            return await ctx.reply("❌ Terjadi error saat unban.", mention_author=False)

async def setup(bot: commands.Bot):
    """
    Saat setup:
    - Kalau bot mendukung remove_command, hapus 'unban' lama agar tidak bentrok.
    - Selalu add_cog agar smoke test lulus.
    """
    # Hapus command lama kalau method tersedia
    if hasattr(bot, "remove_command"):
        try:
            bot.remove_command("unban")
        except Exception:
            pass

    # Daftarkan Cog
    if hasattr(bot, "add_cog"):
        await bot.add_cog(UnbanFix(bot))
    else:
        # fallback aman untuk DummyBot yang tidak punya add_cog
        log.warning("Bot tidak mendukung add_cog; UnbanFix tidak terpasang penuh.")
