
from __future__ import annotations
import os
import discord
from discord.ext import commands
from typing import Optional

from satpambot.utils import translate_utils as tu

DEFAULT_TARGET = os.getenv("TRANSLATE_DEFAULT_TARGET", "en")
DEFAULT_PROVIDER = os.getenv("TRANSLATE_PROVIDER", "auto")  # auto|deep|googletrans

class Translator(commands.Cog):
    """Message translator via context menu & slash command.
    Minimal footprint, works without OpenAI.
    """

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    # Context menu: right click -> Apps -> Translate
    @discord.app_commands.context_menu(name="Translate")
    async def translate_context(self, interaction: discord.Interaction, message: discord.Message):
        target = DEFAULT_TARGET
        provider = DEFAULT_PROVIDER
        text = message.content or ""
        if not text.strip():
            await interaction.response.send_message("Tidak ada teks untuk diterjemahkan.", ephemeral=True)
            return
        out = tu.translate_text(text, target=target, provider=provider)
        detected = tu.detect_lang(text)
        embed = discord.Embed(title=f"Translate -> {target}", description=out)
        embed.set_footer(text=f"detected: {detected} • provider: {provider}")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.app_commands.command(name="translate", description="Terjemahkan teks dengan cepat")
    @discord.app_commands.describe(text="Teks sumber", target="Kode bahasa tujuan (mis. en, id, ja, zh-CN)")
    async def translate_slash(self, interaction: discord.Interaction, text: str, target: Optional[str] = None):
        tgt = (target or DEFAULT_TARGET).strip() or "en"
        out = tu.translate_text(text, target=tgt, provider=DEFAULT_PROVIDER)
        detected = tu.detect_lang(text)
        embed = discord.Embed(title=f"Translate -> {tgt}", description=out)
        embed.set_footer(text=f"detected: {detected} • provider: {DEFAULT_PROVIDER}")
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(Translator(bot))
