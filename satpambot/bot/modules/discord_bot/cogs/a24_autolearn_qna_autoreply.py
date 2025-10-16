
# a24_autolearn_qna_autoreply.py (v7.1)
import re, logging
from discord.ext import commands
log = logging.getLogger(__name__)
class AutoLearnQnAAutoreply(commands.Cog):
    def __init__(self, bot): self.bot = bot
    @commands.Cog.listener()
    async def on_message(self, message):
        try:
            if not self.bot.user or message.author.id != self.bot.user.id: return
            text = (message.content or "").strip()
            if not text.startswith("[auto-learn]"): return
            m = re.search(r"^Q:\s*(.+)$", text, re.MULTILINE)
            if not m: return
            q = m.group(1).strip()
            ask = getattr(self.bot, "llm_ask", None)
            if not ask: log.info("[autolearn] llm provider not ready"); return
            ans = await ask(q, system="Jawab ringkas, fokus langkah praktis. Bahasa Indonesia.", temperature=0.3)
            if not ans: log.info("[autolearn] no answer"); return
            if message.thread and (getattr(message.thread, "archived", False) is False):
                await message.thread.send(f"[auto-learn:answer]\nA: {ans}")
            else:
                await message.channel.send(f"[auto-learn:answer]\n**Q:** {q}\n**A:** {ans}", reference=message)
        except Exception as e:
            log.info("[autolearn] on_message failed: %r", e)
async def setup(bot):
    try: await bot.add_cog(AutoLearnQnAAutoreply(bot))
    except Exception as e: log.info("[autolearn] setup swallowed: %r", e)
