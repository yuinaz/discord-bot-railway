"""Discord translator Cog.
Safe on import: no network calls or heavy side effects at import time.
"""
from __future__ import annotations

import typing as _t

try:
    import discord
    from discord.ext import commands
except Exception:  # pragma: no cover
    # Allow import to succeed in environments without discord.py (smoke/import only)
    discord = None  # type: ignore
    commands = object  # type: ignore

# Import lazily inside commands to avoid provider import during smoke
# (translate_utils already lazy-loads providers).
from satpambot.utils.translate_utils import translate_text


class Translator(commands.Cog if hasattr(commands, 'Cog') else object):  # type: ignore
    """Adds a /translate command (hybrid)."""

    def __init__(self, bot):
        self.bot = bot

    if hasattr(commands, 'hybrid_command'):
        @commands.hybrid_command(name="translate", with_app_command=True, description="Translate text (default to Indonesian)")
        async def translate_cmd(self, ctx, *, text: str):
            """/translate <text> -> Indonesian (id) by default.
            Use: /translate text:"hello"
            """
            try:
                translated = translate_text(text, target_lang="id", source_lang="auto")
            except Exception as e:
                translated = f"[Translator error] {e}"
            if hasattr(discord, 'Embed'):
                embed = discord.Embed(title="Translation", description=translated)  # type: ignore
                embed.set_footer(text="SatpamBot Translator")
                await ctx.reply(embed=embed)  # type: ignore
            else:
                await ctx.reply(translated)  # type: ignore

async def setup(bot):
    if hasattr(commands, 'Cog'):
        await bot.add_cog(Translator(bot))  # type: ignore
