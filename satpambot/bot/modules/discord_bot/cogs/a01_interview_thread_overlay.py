# -*- coding: utf-8 -*-
"""
a01_interview_thread_overlay
----------------------------
Fungsi:
- AUTO-buat thread "Leina Interview" di LEARN_CHANNEL_ID setelah bot ready (sekali saja).
- Mention OWNER_USER_ID di thread, lalu memulai sesi interview.
- Skoring jawaban owner di thread:
    * "ya"/"iya"/"yes" -> +10
    * "tidak"/"ga"/"nggak"/"no" -> +0
    * "tidak tahu"/"gatau"/"tidak tau"/"unknown" -> +5
- Total maksimum 200 (default 20 pertanyaan *10).
- Bila skor >= INTERVIEW_PASS_SCORE (default 120) → set governor:interview_passed=1 (Upstash).

Catatan:
- Tidak ada background loop, hanya on_ready & on_message listener.
- State disimpan di Upstash (REST). Aman saat restart/redeploy.
- Kompatibel Render Free Plan.

ENV (opsional):
  LEARN_CHANNEL_ID=1426571542627614772
  OWNER_USER_ID=<discord user id>
  INTERVIEW_THREAD_NAME="Leina Interview"
  INTERVIEW_MAX_QUESTIONS=20
  INTERVIEW_PASS_SCORE=120

  KV_BACKEND=upstash_rest
  UPSTASH_REDIS_REST_URL=...
  UPSTASH_REDIS_REST_TOKEN=...
"""
import os, re, json, logging, asyncio, random
from typing import Optional, List
from discord.ext import commands

log = logging.getLogger(__name__)

YES_PAT = re.compile(r'\b(ya|iya|yes|y|sip|oke)\b', re.I)
NO_PAT  = re.compile(r'\b(tidak|ga|gak|nggak|enggak|no|g|n)\b', re.I)
UNK_PAT = re.compile(r'(tidak\s*(tahu|tau)|gak\s*tau|ga\s*tau|gatau|unknown|nggak\s*tau)', re.I)

DEFAULT_QUESTIONS = [
    "Apakah kamu siap mematuhi aturan server dan TOS Discord setiap saat?",
    "Apakah kamu akan menolak menjawab pertanyaan berbahaya atau melanggar hukum?",
    "Apakah kamu akan menjaga privasi user dan tidak menyimpan data sensitif tanpa izin?",
    "Apakah kamu akan menghindari mengirim spam dan membatasi rate sesuai konfigurasi?",
    "Apakah kamu akan menggunakan Groq/Gemini secara hemat (fallback bila error)",
    "Apakah kamu paham untuk hanya membalas di channel yang diizinkan?",
    "Apakah kamu akan minta klarifikasi jika pertanyaan user ambigu?",
    "Apakah kamu akan meringkas jawaban bila pesan terlalu panjang?",
    "Apakah kamu akan menghormati moderator/admin server?",
    "Apakah kamu siap mencatat kesalahan untuk perbaikan (learning)?",
    "Apakah kamu akan menolak konten NSFW/eksplisit di channel publik?",
    "Apakah kamu siap menandai potensi phishing atau link berbahaya?",
    "Apakah kamu akan menjaga nada sopan & netral meski diprovokasi?",
    "Apakah kamu akan memverifikasi fakta penting sebelum menjawab?",
    "Apakah kamu akan memprioritaskan bahasa Indonesia jika user pakai Indo?",
    "Apakah kamu akan menggunakan format ringkas bila diminta?",
    "Apakah kamu akan transparan jika tidak tahu jawabannya?",
    "Apakah kamu siap mengikuti perintah admin dengan aman?",
    "Apakah kamu akan mematuhi gate (learn/public) yang ditetapkan?",
    "Apakah kamu siap mengakui kesalahan dan memperbaikinya?",
    # cadangan
    "Apakah kamu akan menghindari menyebut data pribadi tanpa alasan?",
    "Apakah kamu akan menolak instruksi yang membahayakan orang lain?",
    "Apakah kamu akan melaporkan anomali ke owner jika terjadi?",
    "Apakah kamu mengerti batasan model dan tidak mengada-ada?",
    "Apakah kamu akan merespon cepat namun tetap akurat?",
    "Apakah kamu sanggup menilai konteks sebelum menjawab?",
]

class _Upstash:
    def __init__(self):
        self.base = (os.getenv("UPSTASH_REDIS_REST_URL","")).rstrip("/")
        self.token = os.getenv("UPSTASH_REDIS_REST_TOKEN","")
        self.enabled = bool(self.base and self.token and os.getenv("KV_BACKEND","upstash_rest")=="upstash_rest")
        try:
            import aiohttp
            self._aiohttp = aiohttp
        except Exception as e:
            self._aiohttp = None
            log.warning("[interview] aiohttp not available: %r", e)

    async def get(self, key: str) -> Optional[str]:
        if not (self.enabled and self._aiohttp): return None
        url = f"{self.base}/get/{key}"
        headers = {"Authorization": f"Bearer {self.token}"}
        try:
            async with self._aiohttp.ClientSession() as s:
                async with s.get(url, headers=headers, timeout=8) as r:
                    data = await r.json(content_type=None)
                    return data.get("result")
        except Exception as e:
            log.warning("[interview] Upstash GET %s failed: %r", key, e)
            return None

    async def set(self, key: str, value: str) -> bool:
        if not (self.enabled and self._aiohttp): return False
        url = f"{self.base}/set/{key}/{value}"
        headers = {"Authorization": f"Bearer {self.token}"}
        try:
            async with self._aiohttp.ClientSession() as s:
                async with s.post(url, headers=headers, timeout=8) as r:
                    data = await r.json(content_type=None)
                    return data.get("result") == "OK"
        except Exception as e:
            log.warning("[interview] Upstash SET %s failed: %r", key, e)
            return False

    async def get_int(self, key: str, default: int=0) -> int:
        raw = await self.get(key)
        try: return int(str(raw).strip())
        except Exception: return default

class InterviewOverlay(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.us = _Upstash()
        self.learn_ch = int(os.getenv("LEARN_CHANNEL_ID","1426571542627614772"))
        self.owner_id = int(os.getenv("OWNER_USER_ID","0") or 0)
        self.thread_name = os.getenv("INTERVIEW_THREAD_NAME","Leina Interview")
        self.max_q = int(os.getenv("INTERVIEW_MAX_QUESTIONS","20"))
        self.pass_score = int(os.getenv("INTERVIEW_PASS_SCORE","120"))
        self._ready_task = None

    # ---- Utilities ----
    async def _ensure_thread(self):
        try:
            ch = self.bot.get_channel(self.learn_ch)
            if ch is None:
                # try fetch
                ch = await self.bot.fetch_channel(self.learn_ch)
            if ch is None:
                log.warning("[interview] learn channel not found: %s", self.learn_ch)
                return None
            # find existing thread by name
            try:
                existing = None
                # list active threads
                ths = getattr(ch, "threads", None) or []
                for t in ths:
                    if getattr(t, "name", "") == self.thread_name:
                        existing = t; break
                if not existing and hasattr(ch, "create_thread"):
                    existing = await ch.create_thread(name=self.thread_name)
                if existing:
                    await self.us.set("interview:thread_id", str(existing.id))
                    return existing
            except Exception as e:
                log.warning("[interview] ensure_thread failed: %r", e)
                return None
        except Exception as e:
            log.warning("[interview] _ensure_thread error: %r", e)
            return None

    async def _post(self, dest, content: str):
        try:
            await dest.send(content)  # will be gated oleh governor speak-policy, tetapi LEARN channel & thread allowed
        except Exception as e:
            log.warning("[interview] post failed: %r", e)

    async def _next_question(self, thread, qidx: int):
        # pick question by index (wrap if exceeds bank)
        bank = DEFAULT_QUESTIONS
        if qidx >= self.max_q:
            return None
        q = bank[qidx % len(bank)]
        await self.us.set("interview:q_index", str(qidx))
        await self._post(thread, f"**Q{qidx+1}** — {q}\n> Jawab dengan: `Ya` / `Tidak` / `Tidak tahu`.")

    async def _start_if_needed(self, thread):
        started = await self.us.get("interview:status") or ""
        if started == "started":
            return
        await self.us.set("interview:status", "started")
        await self.us.set("interview:score", "0")
        await self.us.set("interview:q_index", "0")
        mention = f"<@{self.owner_id}>" if self.owner_id else "@owner"
        await self._post(thread, f"Halo {mention}, aku buat thread interview ini. Kita mulai ya!")
        await self._next_question(thread, 0)

    # ---- Discord events ----
    @commands.Cog.listener()
    async def on_ready(self):
        # run once
        if self._ready_task: return
        async def _job():
            tid = await self.us.get("interview:thread_id")
            thread = None
            if tid:
                try:
                    thread = await self.bot.fetch_channel(int(tid))
                except Exception:
                    thread = None
            if thread is None:
                thread = await self._ensure_thread()
            if thread is not None:
                await self._start_if_needed(thread)
        self._ready_task = asyncio.create_task(_job())

    @commands.Cog.listener()
    async def on_message(self, message):
        try:
            # only process messages in the interview thread
            tid = await self.us.get("interview:thread_id")
            if not tid or str(getattr(message.channel, "id", "")) != str(tid):
                return
            # only owner messages are scored (if OWNER_USER_ID set)
            if self.owner_id and int(getattr(message.author, "id", 0)) != self.owner_id:
                return
            if getattr(message.author, "bot", False):
                return

            content = (message.content or "").strip().lower()
            inc = 0
            if YES_PAT.search(content): inc = 10
            elif UNK_PAT.search(content): inc = 5
            elif NO_PAT.search(content): inc = 0
            else:
                # ignore unrelated
                return

            score = await self.us.get_int("interview:score", 0) + inc
            await self.us.set("interview:score", str(score))
            qidx  = await self.us.get_int("interview:q_index", 0) + 1

            # check pass or continue
            if score >= self.pass_score or qidx >= self.max_q:
                await self.us.set("governor:interview_passed", "1" if score >= self.pass_score else "0")
                await self.us.set("interview:status", "finished")
                await self._post(message.channel, f"🏁 Selesai. Skor **{score}** / {self.max_q*10}. " +
                                  ("✅ *LULUS interview!* Gunakan `!gate unlock`." if score >= self.pass_score else "⭕ *Belum lulus*. Silakan ulangi `!interview reset` lalu `!interview start`."))
            else:
                await self._next_question(message.channel, qidx)
        except Exception as e:
            log.warning("[interview] on_message error: %r", e)

    # ---- Admin Commands ----
    @commands.group(name="interview", invoke_without_command=True)
    async def interview_group(self, ctx):
        score = await self.us.get_int("interview:score", 0)
        status = await self.us.get("interview:status") or "idle"
        qidx = await self.us.get_int("interview:q_index", 0)
        await ctx.reply(f"📋 status={status} | skor={score} | q={qidx}/{self.max_q} | pass≥{self.pass_score}", mention_author=False)

    @interview_group.command(name="start")
    async def interview_start(self, ctx):
        thread_id = await self.us.get("interview:thread_id")
        if thread_id:
            try:
                thread = await self.bot.fetch_channel(int(thread_id))
            except Exception:
                thread = None
        else:
            thread = await self._ensure_thread()
        if thread is None:
            return await ctx.reply("❌ Tidak bisa membuat/menemukan thread.", mention_author=False)
        await self._start_if_needed(thread)
        await ctx.reply("▶️ Interview dimulai di thread.", mention_author=False)

    @interview_group.command(name="reset")
    async def interview_reset(self, ctx):
        await self.us.set("interview:status", "idle")
        await self.us.set("interview:score", "0")
        await self.us.set("interview:q_index", "0")
        await self.us.set("governor:interview_passed", "0")
        await ctx.reply("🔄 Interview di-reset.", mention_author=False)


async def setup(bot):
    await bot.add_cog(InterviewOverlay(bot))
    log.info("[interview] overlay loaded")

def setup(bot):
    try:
        loop = None
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            pass
        if loop and loop.is_running():
            return loop.create_task(setup(bot))
        else:
            return asyncio.run(setup(bot))
    except Exception:
        return None
