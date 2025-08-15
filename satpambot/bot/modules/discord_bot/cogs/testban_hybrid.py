from __future__ import annotations
from typing import Optional
import discord
from discord.ext import commands
from ..helpers.ban_embed import build_ban_embed
from satpambot.bot.modules.discord_bot.helpers.permissions import is_mod_or_admin
def _allowed_mentions_for(target: Optional[discord.Member]) -> discord.AllowedMentions:
    return discord.AllowedMentions(users=[target] if target else [], roles=False, everyone=False, replied_user=False)
class TestbanHybrid(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    async def _send_simulation(self, ctx_or_inter, member: Optional[discord.Member] = None):
        author = (ctx_or_inter.user if isinstance(ctx_or_inter, discord.Interaction) else ctx_or_inter.author)
        if not isinstance(author, discord.Member) or not is_mod_or_admin(author):
            msg = '❌ Kamu tidak punya izin untuk menjalankan perintah ini.'
            if isinstance(ctx_or_inter, discord.Interaction):
                await ctx_or_inter.response.send_message(msg, ephemeral=True)
            else:
                await ctx_or_inter.send(msg); return
        target = member or (author if isinstance(author, discord.Member) else None)
        emb = build_ban_embed(target or author, simulated=True)
        allowed = _allowed_mentions_for(target or author)
        if isinstance(ctx_or_inter, discord.Interaction):
            if not ctx_or_inter.response.is_done():
                await ctx_or_inter.response.send_message(embed=emb, allowed_mentions=allowed)
            else:
                await ctx_or_inter.followup.send(embed=emb, allowed_mentions=allowed)
        else:
            await ctx_or_inter.send(embed=emb, allowed_mentions=allowed)
    @commands.hybrid_command(name='testban', description='Simulasi ban (embed saja).', with_app_command=True)
    async def testban_cmd(self, ctx: commands.Context, member: Optional[discord.Member] = None):
        await self._send_simulation(ctx, member)
    @commands.hybrid_command(name='tb', description='Alias dari testban (embed saja).', with_app_command=True)
    async def tb_cmd(self, ctx: commands.Context, member: Optional[discord.Member] = None):
        await self._send_simulation(ctx, member)
    @commands.Cog.listener() async def on_ready(self):
        try: self.bot.remove_command('testban'); self.bot.remove_command('tb')
        except Exception: pass
async def setup(bot: commands.Bot):
    try: bot.remove_command('testban'); bot.remove_command('tb')
    except Exception: pass
    await bot.add_cog(TestbanHybrid(bot))
