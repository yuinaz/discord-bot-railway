
from __future__ import annotations
import asyncio
from typing import Optional, Union
import discord
from discord import app_commands
from discord.ext import commands

LOG = __import__("logging").getLogger("satpambot.bot.modules.discord_bot.cogs.a08_public_clearchat")
TargetChoice = app_commands.Choice[str]

GuildChan = Union[discord.TextChannel, discord.Thread, discord.ForumChannel]

class ClearChatHybrid(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="clearchat", description="Bersihkan pesan (DM/guild). Bisa filter embed, webhooks, judul embed.")
    @app_commands.describe(
        limit="Jumlah pesan yang discan (1-2000)",
        target="bot / user / all (guild only)",
        user="User target (untuk target=user)",
        channel="Channel/Thread lain (opsional). Default: channel sekarang",
        skip_pinned="Lewati pinned (default: true)",
        only_embeds="Hanya pesan yang punya embed (default: false)",
        title_contains="Jika only_embeds=true, hapus yang judul embed mengandung teks ini",
        from_webhooks="Hanya pesan dari webhook (default: false)",
        dry_run="Simulasi saja, tidak menghapus (default: false)",
    )
    @app_commands.choices(target=[
        TargetChoice(name="Bot saja", value="bot"),
        TargetChoice(name="User tertentu", value="user"),
        TargetChoice(name="Semua (moderation)", value="all"),
    ])
    async def clearchat(
        self, interaction: discord.Interaction,
        limit: app_commands.Range[int,1,2000]=200,
        target: Optional[TargetChoice]=None,
        user: Optional[discord.Member]=None,
        channel: Optional[GuildChan]=None,
        skip_pinned: bool=True,
        only_embeds: bool=False,
        title_contains: Optional[str]=None,
        from_webhooks: bool=False,
        dry_run: bool=False,
    ):
        ch = channel or interaction.channel
        me = interaction.client.user
        if me is None or ch is None:
            await interaction.response.send_message("Bot belum siap.", ephemeral=True); return
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True, thinking=True)

        # DM mode
        if isinstance(ch, (discord.DMChannel, discord.PartialMessageable, discord.GroupChannel)):
            deleted=0; scanned=0; errors=0
            async for msg in ch.history(limit=limit, oldest_first=False):
                scanned += 1
                if msg.author.id != me.id: continue
                if only_embeds and not msg.embeds: continue
                if from_webhooks and not msg.webhook_id: continue
                if title_contains and not any((e.title or "").lower().find(title_contains.lower())>=0 for e in msg.embeds):
                    continue
                if dry_run: continue
                try:
                    await msg.delete(); deleted+=1
                except discord.Forbidden: errors+=1
                except discord.HTTPException: errors+=1; await asyncio.sleep(0.35)
                if deleted and deleted%10==0: await asyncio.sleep(0.25)
            await interaction.followup.send(f"✅ DM: {deleted} dihapus (scan {scanned}){' [dry-run]' if dry_run else ''}.", ephemeral=True)
            return

        # Guild mode (TextChannel/Thread/Forum)
        if not isinstance(ch, (discord.TextChannel, discord.Thread, discord.ForumChannel)):
            await interaction.followup.send("Perintah ini hanya untuk DM atau channel server.", ephemeral=True); return

        # If forum channel given, operate on the selected forum's parent but history() isn't supported.
        if isinstance(ch, discord.ForumChannel):
            await interaction.followup.send("ForumChannel tidak mendukung 'history' langsung. Jalankan di Thread atau TextChannel.", ephemeral=True)
            return

        guild = ch.guild
        me_m = guild.get_member(me.id)
        inv = interaction.user if isinstance(interaction.user, discord.Member) else guild.get_member(interaction.user.id)  # type: ignore
        if not me_m or not inv:
            await interaction.followup.send("Gagal membaca permission.", ephemeral=True); return
        if not ch.permissions_for(me_m).read_message_history:
            await interaction.followup.send("Bot butuh **Read Message History** di channel ini.", ephemeral=True); return

        mode = (target.value if isinstance(target, app_commands.Choice) else (target or "bot")).lower()
        tgt_m = None
        if mode=="user":
            if not user: await interaction.followup.send("Pilih **user** saat target=user.", ephemeral=True); return
            tgt_m = user
            if not (ch.permissions_for(me_m).manage_messages and ch.permissions_for(inv).manage_messages):
                await interaction.followup.send("Butuh **Manage Messages** untuk bot & invoker.", ephemeral=True); return
        if mode=="all" or from_webhooks:
            if not (ch.permissions_for(me_m).manage_messages and ch.permissions_for(inv).manage_messages):
                await interaction.followup.send("Mode `all`/webhook butuh **Manage Messages** untuk bot & invoker.", ephemeral=True); return

        deleted=0; scanned=0; errors=0
        async for msg in ch.history(limit=limit, oldest_first=False):
            scanned+=1
            if skip_pinned and msg.pinned: continue
            if only_embeds and not msg.embeds: continue
            if title_contains and not any((e.title or "").lower().find(title_contains.lower())>=0 for e in msg.embeds):
                continue
            if from_webhooks and not msg.webhook_id: continue
            if mode=="bot" and msg.author.id!=me.id: continue
            if mode=="user" and (not tgt_m or msg.author.id!=tgt_m.id): continue
            if dry_run: continue
            try:
                await msg.delete(); deleted+=1
            except discord.Forbidden: errors+=1
            except discord.HTTPException: errors+=1; await asyncio.sleep(0.35)
            if deleted and deleted%10==0: await asyncio.sleep(0.25)
        detail = f"✅ {'Thread' if isinstance(ch, discord.Thread) else 'Guild'}: {deleted} dihapus (scan {scanned})"
        if mode!="bot": detail += f" mode={mode}"
        if from_webhooks: detail += " from_webhooks=true"
        if only_embeds: detail += " (only embeds)"
        if title_contains: detail += f" title~='{title_contains}'"
        if dry_run: detail += " [dry-run]"
        if errors: detail += f" — ⚠️ {errors} gagal (izin/limit)."
        await interaction.followup.send(detail, ephemeral=True)

async def setup(bot: commands.Bot):
    res = await bot.add_cog(ClearChatHybrid(bot))
    import asyncio as _aio
    if _aio.iscoroutine(res): await res