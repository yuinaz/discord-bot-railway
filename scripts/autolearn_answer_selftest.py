# Offline selftest untuk alur answer tanpa Discord (hanya panggil fallback LLM).
import asyncio, os, sys
from satpambot.bot.modules.discord_bot.helpers.llm_fallback_min import groq_chat, gemini_chat

async def main(q: str):
    system = "Jawab ringkas dan jelas (Bahasa Indonesia)."
    prov = os.getenv("LLM_PROVIDER","groq").lower()
    if prov == "gemini":
        ans = await gemini_chat(q, system=system)
    else:
        ans = await groq_chat(q, system=system)
    print("Q:", q)
    print("A:", ans[:400])

if __name__ == "__main__":
    q = "Apa cara sederhana menjelaskan overfitting?"
    if len(sys.argv) > 1:
        q = " ".join(sys.argv[1:])
    asyncio.run(main(q))
