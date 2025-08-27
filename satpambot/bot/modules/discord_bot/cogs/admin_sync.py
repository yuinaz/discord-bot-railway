
from __future__ import annotations

import discord
from discord import app_commands, Interaction
from discord.ext import commands
from typing import Literal, Optional

def _has_manage(inter: Interaction) -> bool:
    if inter.user and isinstance(inter.user, discord.Member):
        p = inter.user.guild_permissions
        return p.manage_guild or p.administrator
    return False

class AdminSync(commands.Cog):
    """Slash-command sync utility.
    Avoids naming collisions by NOT calling the handler 'sync' internally.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="sync", description="Sync slash commands (default: this guild).")
    @app_commands.describe(
        scope="Pilih cakupan sinkronisasi",
        guild_id="Opsional: ID guild untuk target (kalau kosong, pakai guild sekarang)",
    )
    async def do_sync(
        self,
        inter: Interaction,
        scope: Literal["guild", "global", "copy_global_to_guild", "clear_guild"] = "guild",
        guild_id: Optional[str] = None,
    ) -> None:
        if not _has_manage(inter):
            return await inter.response.send_message("❌ Kamu butuh izin Manage Guild.", ephemeral=True)

        try:
            await inter.response.defer(ephemeral=True, thinking=True)
        except discord.InteractionResponded:
            pass

        try:
            # Tentukan target guild (kalau perlu)
            target_guild = None
            if scope != "global":
                if guild_id and guild_id.isdigit():
                    target_guild = discord.Object(id=int(guild_id))
                elif inter.guild:
                    target_guild = inter.guild
                else:
                    return await inter.followup.send("❌ Tidak ada guild context.", ephemeral=True)

            if scope == "guild":
                synced = await self.bot.tree.sync(guild=target_guild)
                return await inter.followup.send(f"✅ Synced **{len(synced)}** command ke guild **{getattr(target_guild, 'id', '?')}**.", ephemeral=True)

            if scope == "copy_global_to_guild":
                # copy global commands ke guild lalu sync
                self.bot.tree.copy_global_to(guild=target_guild)
                synced = await self.bot.tree.sync(guild=target_guild)
                return await inter.followup.send(f"✅ Copied+Synced **{len(synced)}** command ke guild **{getattr(target_guild, 'id', '?')}**.", ephemeral=True)

            if scope == "clear_guild":
                self.bot.tree.clear_commands(guild=target_guild)
                await self.bot.tree.sync(guild=target_guild)
                return await inter.followup.send(f"🧹 Cleared commands untuk guild **{getattr(target_guild, 'id', '?')}**.", ephemeral=True)

            # scope == "global"
            synced = await self.bot.tree.sync()
            return await inter.followup.send(f"🌍 Synced global: **{len(synced)}** command.", ephemeral=True)

        except Exception as e:
            return await inter.followup.send(f"❌ Sync gagal: `{e}`", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(AdminSync(bot))
