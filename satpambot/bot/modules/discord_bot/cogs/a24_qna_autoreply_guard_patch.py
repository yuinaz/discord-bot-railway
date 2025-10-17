
"""
QNA auto-reply guard patch:
- If original autoreply produces "no answer" or fails, we post a fallback embed.
- Works only in QNA_CHANNEL_ID (env or overlay variable).
"""
from __future__ import annotations
import os, logging, asyncio
import discord

log = logging.getLogger(__name__)

def _qna_channel_id(bot) -> int | None:
    # prefer overlay globals if present
    for m in (
        "satpambot.bot.modules.discord_bot.cogs.a24_qna_channel_overlay",
        "satpambot.bot.modules.discord_bot.cogs.a00_render_runtime_guard",
        "satpambot.bot.modules.discord_bot.cogs.qna_dual_provider",
        "satpambot.bot.modules.discord_bot.cogs.selfheal_learning_bridge",
    ):
        try:
            mod = __import__(m, fromlist=["*"])
            cid = getattr(mod, "QNA_CHANNEL_ID", None)
            if cid:
                return int(cid)
        except Exception:
            pass
    env = os.getenv("QNA_CHANNEL_ID")
    return int(env) if env and env.isdigit() else None

class QnaFallback(discord.Cog):
    def __init__(self, bot: discord.Client):
        self.bot = bot

    @discord.Cog.listener("on_message")
    async def on_message(self, msg: discord.Message):
        if msg.author.bot:  # ignore bots to prevent loops
            return
        cid = _qna_channel_id(self.bot)
        if not cid or msg.channel.id != cid:
            return

        # Give original cog a small window to respond
        await asyncio.sleep(2.0)

        # If there is already an assistant reply in last few messages, skip
        try:
            history = [m async for m in msg.channel.history(limit=6)]
            for m in history:
                if m.id == msg.id:  # skip the question itself
                    continue
                if m.author.bot and (m.reference and m.reference.message_id == msg.id):
                    return  # someone already replied referencing this message
        except Exception:
            pass

        # Fallback ask via bot.llm_ask
        ask = getattr(self.bot, "llm_ask", None)
        if not ask:
            log.warning("[qna-fallback] bot.llm_ask not ready")
            return

        question = msg.content.strip()
        try:
            answer = await ask(question, prefer="auto")
        except Exception as e:
            log.warning("[qna-fallback] ask failed: %r", e)
            return

        # Build embed Q/A
        emb = discord.Embed(title="QnA", description="Auto-learn reply", colour=discord.Colour.blurple())
        emb.add_field(name="Question (Leina)", value=question[:1024] or "—", inline=False)
        emb.add_field(name="Answer (LLM)", value=answer[:1024] or "—", inline=False)
        emb.set_footer(text="providers: Groq/Gemini • fallback-path")

        try:
            await msg.channel.send(embed=emb, reference=msg)
        except Exception as e:
            log.warning("[qna-fallback] send failed: %r", e)

async def setup(bot):
    try:
        await bot.add_cog(QnaFallback(bot))
        log.info("[qna-fallback] installed")
    except Exception as e:
        log.warning("[qna-fallback] setup failed: %r", e)
