from __future__ import annotations
import logging, json, contextlib, importlib
import discord
from discord.ext import commands, tasks
from satpambot.config.local_cfg import cfg
from satpambot.shared.selfheal_queue import enqueue_ticket, list_tickets, update_ticket

log = logging.getLogger(__name__)

def _make_groq_client():
    for modpath in ["satpambot.bot.llm.groq_client","satpambot.ai.groq_client","satpambot.bot.llm._groq_client_suite"]:
        try:
            m = importlib.import_module(modpath)
            fn = getattr(m, "make_groq_client", None) or getattr(m, "get_client", None)
            if callable(fn): return fn()
        except Exception:
            continue
    return None

def _selfheal_router():
    for modpath in [
        "satpambot.bot.modules.discord_bot.cogs.selfheal_router",
        "modules.discord_bot.cogs.selfheal_router",
    ]:
        try:
            return importlib.import_module(modpath)
        except Exception:
            pass
    return None

class _RepeatingLogCapture(logging.Handler):
    def __init__(self, min_level=logging.WARNING):
        super().__init__(level=min_level)
        self.last = {}
    def emit(self, record):
        try:
            msg = record.getMessage()
            where = f"{record.name}:{getattr(record, 'funcName', '')}"
            key = f"{record.levelno}:{where}:{msg.strip()[:200]}"
            now = record.created
            if now - self.last.get(key, 0.0) < 15:
                return
            self.last[key] = now
            enqueue_ticket({"level": record.levelname, "message": msg, "where": where, "time": now})
        except Exception:
            pass

class SelfHealCoordinator(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._handler = _RepeatingLogCapture(min_level=logging.WARNING)

    async def cog_load(self):
        try:
            logging.getLogger().addHandler(self._handler)
            if cfg("SELFHEAL_ENABLE", "1") not in (0, False, "0", "false"):
                self._tick_process.start()
            log.info("[selfheal] coordinator online (enable=%s)", cfg("SELFHEAL_ENABLE", "1"))
        except Exception as e:
            log.error("[selfheal] failed to start: %s", e)

    def cog_unload(self):
        with contextlib.suppress(Exception):
            logging.getLogger().removeHandler(self._handler)
        with contextlib.suppress(Exception):
            if hasattr(self, "_tick_process"):
                self._tick_process.cancel()

    @tasks.loop(seconds=60)
    async def _tick_process(self):
        tickets = []
        with contextlib.suppress(Exception):
            tickets = list_tickets()
        for t in tickets:
            if t.get("status") != "queued":
                continue
            if str(t.get("level")).upper() not in ("WARNING","ERROR","CRITICAL"):
                continue
            groq = _make_groq_client()
            diag = {"note": "Groq disabled or not configured."}
            if groq:
                try:
                    prompt = (
                        "You are a Python/Discord-bot repair assistant. "
                        "Given a warning/error log, infer the likely import/path/config issue. "
                        "Respond JSON: {\"root_cause\": str, \"suggestion\": str, "
                        "\"patch\": [{\"file\": str, \"find\": str, \"replace\": str}]}."
                    )
                    text = json.dumps({"level": t.get("level"), "where": t.get("where"), "message": t.get("message")})
                    try:
                        comp = groq.chat.completions.create(
                            model=cfg("GROQ_MODEL","llama-3.1-8b-instant"),
                            messages=[{"role":"system","content":prompt},{"role":"user","content":text}],
                            temperature=0.2,
                        )
                        content = comp.choices[0].message.content
                    except Exception:
                        content = ""
                    with contextlib.suppress(Exception):
                        diag = json.loads(content)
                except Exception:
                    pass
            update_ticket(t.get("id",""), status="diagnosed", diagnosis=diag)
            router = _selfheal_router()
            if router and hasattr(router, "send_selfheal"):
                try:
                    emb = discord.Embed(
                        title=f"Self-Heal Ticket {t.get('id','?')}",
                        description=f"**{t.get('level')}** at `{t.get('where')}`\n{(t.get('message') or '')[:300]}",
                        colour=discord.Colour.orange(),
                    )
                    if isinstance(diag, dict) and "root_cause" in diag:
                        emb.add_field(name="Diagnosis", value=str(diag.get("root_cause"))[:512], inline=False)
                    if isinstance(diag, dict) and "suggestion" in diag:
                        emb.add_field(name="Suggestion", value=str(diag.get("suggestion"))[:512], inline=False)
                    await router.send_selfheal(self.bot, emb)
                except Exception:
                    pass

async def setup(bot: commands.Bot):
    try:
        await bot.add_cog(SelfHealCoordinator(bot))
    except Exception as e:
        log.error("Failed to add SelfHealCoordinator: %s", e)