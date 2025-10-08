# satpambot/bot/modules/discord_bot/cogs/selfheal_groq_agent.py
from __future__ import annotations
import os, json, time, asyncio, logging
from typing import List, Dict, Any, Optional, Tuple
import discord
from discord.ext import commands, tasks

# Groq client (optional)
try:
    from groq import Groq
    _HAS_GROQ = True
except Exception:
    _HAS_GROQ = False

from satpambot.config.runtime import cfg, set_cfg

# Router to send embeds to log channel/owner
async def _send_embed(bot: commands.Bot, title: str, description: str, color: int = 0x2ecc71):
    try:
        from .selfheal_router import send_selfheal
        await send_selfheal(bot, discord.Embed(title=title, description=description, color=color))
    except Exception:
        # best-effort fallback: try owner DM
        try:
            owner = (bot.owner_id and bot.get_user(bot.owner_id)) or None
            if owner:
                await owner.send(embed=discord.Embed(title=title, description=description, color=color))
        except Exception:
            pass

# safe JSON schema
_ALLOWED_ACTIONS = {"set_cfg", "reload_extension", "send_log"}

SYSTEM_PROMPT = (
    "You are a reliable maintenance planner for a Discord moderation bot. "
    "You will receive recent log lines and settings. "
    "Reply with a STRICT JSON object with fields: "
    "{'risk':'low|medium|high','reason':'short text',"
    "'actions':[{'op':'set_cfg','key':'STR','value':STR|INT|BOOL}|"
    "{'op':'reload_extension','name':'python.module.path'}|"
    "{'op':'send_log','message':'short text'}]} . "
    "Only use allowed ops. Keep actions minimal and safe. "
    "Prefer configuration tweaks over restarts. "
    "If nothing to do, return {'risk':'low','reason':'noop','actions':[]}."
)

class _BufferingHandler(logging.Handler):
    def __init__(self, agent: 'SelfHealGroqAgent'):
        super().__init__(level=logging.WARNING)  # capture WARNING+
        self.agent = agent
        self.setFormatter(logging.Formatter("%(levelname)s:%(name)s:%(message)s"))
    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            self.agent._push_log(msg)
        except Exception:
            pass

class SelfHealGroqAgent(commands.Cog):
    """Self-heal agent using Groq: aggregates errors, plans safe actions, and optionally applies them."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.buf: List[Tuple[float, str]] = []
        self.last_apply_ts: float = 0.0
        self.applied_in_window: int = 0
        self.window_start_ts: float = time.time()
        self.handler: Optional[_BufferingHandler] = None

    async def cog_load(self):
        # Defaults (quiet by default)
        defaults = {
            "SELFHEAL_ENABLE": True,
            "SELFHEAL_ANALYZE_INTERVAL_S": 600,   # 10 minutes
            "SELFHEAL_AUTO_APPLY_SAFE": True,
            "SELFHEAL_MAX_ACTIONS_PER_HOUR": 3,
            "SELFHEAL_DM_SUMMARY": False,         # reduce DM noise
            "SELFHEAL_ALLOWED_ACTIONS": ",".join(sorted(_ALLOWED_ACTIONS)),
        }
        applied = []
        for k, v in defaults.items():
            if cfg(k) is None:
                set_cfg(k, v); applied.append(f"{k}={v}")
        if applied and bool(cfg("SELFHEAL_DM_SUMMARY", False)):
            await _send_embed(self.bot, "Self-Heal Defaults", "Applied: \n- " + "\n- ".join(applied))

        # Install logging handler
        self.handler = _BufferingHandler(self)
        logging.getLogger().addHandler(self.handler)

        # Start periodic analysis
        self._loop.change_interval(seconds=int(cfg("SELFHEAL_ANALYZE_INTERVAL_S", 600)))
        self._loop.start()

    async def cog_unload(self):
        try:
            if self.handler:
                logging.getLogger().removeHandler(self.handler)
        except Exception:
            pass
        try:
            if self._loop.is_running():
                self._loop.cancel()
        except Exception:
            pass

    # Buffer management
    def _push_log(self, text: str) -> None:
        now = time.time()
        self.buf.append((now, text))
        # keep last 200 lines / last 2 hours
        horizon = now - 7200
        self.buf = [(t, s) for (t, s) in self.buf[-200:] if t >= horizon]

    def _recent_logs(self) -> List[str]:
        return [s for (t, s) in self.buf]

    def _window_reset_if_needed(self):
        now = time.time()
        if now - self.window_start_ts > 3600:
            self.window_start_ts = now
            self.applied_in_window = 0

    # Periodic task
    @tasks.loop(seconds=600)
    async def _loop(self):
        if not bool(cfg("SELFHEAL_ENABLE", True)):
            return
        if not _HAS_GROQ:
            return
        if not (os.getenv("GROQ_API_KEY") or cfg("GROQ_API_KEY")):
            return

        logs = self._recent_logs()
        if not logs:
            return

        # Compose messages
        model = str(cfg("GROQ_MODEL", cfg("CHAT_MODEL", "llama-3.1-8b-instant")))
        timeout_s = int(cfg("LLM_TIMEOUT_S", 20))
        client = Groq(api_key=(os.getenv("GROQ_API_KEY") or cfg("GROQ_API_KEY")), timeout=timeout_s)

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps({
                "settings": {
                    "ALLOW": list(_ALLOWED_ACTIONS),
                    "INTERVAL_S": int(cfg("SELFHEAL_ANALYZE_INTERVAL_S", 600)),
                },
                "logs": logs[-50:],
            }, ensure_ascii=False)},
        ]

        try:
            resp = await asyncio.to_thread(lambda: client.chat.completions.create(
                model=model, messages=messages, temperature=0.2, max_tokens=300
            ))
            text = (resp.choices[0].message.content or "").strip()
        except Exception as e:
            await _send_embed(self.bot, "Self-Heal Error", f"LLM call failed: {e}", color=0xe67e22)
            return

        # Parse JSON
        plan = None
        try:
            plan = json.loads(text)
        except Exception:
            # Try to extract JSON blob
            import re
            m = re.search(r"\{.*\}", text, re.S)
            if m:
                try:
                    plan = json.loads(m.group(0))
                except Exception:
                    plan = None

        if not isinstance(plan, dict):
            if bool(cfg("SELFHEAL_DM_SUMMARY", False)):
                await _send_embed(self.bot, "Self-Heal Plan", "No valid JSON; skipping.", color=0xe67e22)
            return

        actions = plan.get("actions") or []
        risk = str(plan.get("risk", "low"))
        reason = str(plan.get("reason", ""))[:300]

        # Filter actions by allowlist
        allow = set(str(cfg("SELFHEAL_ALLOWED_ACTIONS", ",".join(_ALLOWED_ACTIONS))).split(","))
        filtered = [a for a in actions if isinstance(a, dict) and a.get("op") in allow and a.get("op") in _ALLOWED_ACTIONS]

        # Auto-apply logic
        auto = bool(cfg("SELFHEAL_AUTO_APPLY_SAFE", True)) and (risk in ("low", "medium"))
        applied = []
        if auto and filtered:
            self._window_reset_if_needed()
            max_actions = int(cfg("SELFHEAL_MAX_ACTIONS_PER_HOUR", 3))
            if self.applied_in_window >= max_actions:
                await _send_embed(self.bot, "Self-Heal Throttled", f"Reached quota {max_actions}/h; holding.", color=0xe67e22)
            else:
                left = max_actions - self.applied_in_window
                to_apply = filtered[:left]
                for act in to_apply:
                    ok, msg = await self._apply_action(act)
                    applied.append((act, ok, msg))
                    self.applied_in_window += 1
                    await asyncio.sleep(0.5)

        # Summary (goes to log channel by router; not DM unless router is DM)
        if bool(cfg("SELFHEAL_DM_SUMMARY", False)) or applied:
            lines = [f"risk={risk} reason={reason}"]
            if filtered:
                lines.append("actions: " + json.dumps(filtered, ensure_ascii=False))
            if applied:
                lines.append("applied: " + json.dumps([{"op": a[0]["op"], "ok": a[1], "msg": a[2]} for a in applied], ensure_ascii=False))
            await _send_embed(self.bot, "Self-Heal Plan", "\n".join(lines))

    async def _apply_action(self, act: Dict[str, Any]) -> Tuple[bool, str]:
        op = act.get("op")
        try:
            if op == "set_cfg":
                k = str(act.get("key")); v = act.get("value")
                set_cfg(k, v)
                return True, f"set_cfg({k}={v})"
            if op == "reload_extension":
                name = str(act.get("name"))
                await self._safe_reload(name)
                return True, f"reload_extension({name})"
            if op == "send_log":
                msg = str(act.get("message", ""))[:1900]
                await _send_embed(self.bot, "Self-Heal Note", msg or "(empty)")
                return True, "logged"
        except Exception as e:
            return False, f"{type(e).__name__}: {e}"
        return False, "unsupported"

    async def _safe_reload(self, name: str) -> None:
        try:
            if name in self.bot.extensions:
                await self.bot.reload_extension(name)
            else:
                await self.bot.load_extension(name)
        except Exception:
            # ignore failures
            pass

    # Commands
    @commands.hybrid_group(name="selfheal", with_app_command=True, description="Self-Heal (Groq)")
    async def selfheal(self, ctx: commands.Context):
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @selfheal.command(name="status", with_app_command=True)
    async def selfheal_status(self, ctx: commands.Context):
        logs = self._recent_logs()[-5:]
        embed = discord.Embed(title="Self-Heal Status", color=0x95a5a6)
        embed.add_field(name="Enable", value=str(bool(cfg("SELFHEAL_ENABLE", True))), inline=True)
        embed.add_field(name="Auto-Apply", value=str(bool(cfg("SELFHEAL_AUTO_APPLY_SAFE", True))), inline=True)
        embed.add_field(name="Applied/h", value=str(self.applied_in_window), inline=True)
        if logs:
            embed.add_field(name="Recent logs", value="\n".join(l[:120] for l in logs), inline=False)
        await ctx.reply(embed=embed, mention_author=False)

    @selfheal.command(name="dryrun", with_app_command=True, description="Paksa analisa sekarang (tanpa apply)")
    @commands.is_owner()
    async def selfheal_dryrun(self, ctx: commands.Context):
        await ctx.reply("OK. Analisa segera (tanpa apply).", mention_author=False)
        await self._loop()  # run once with current buffer

    @selfheal.command(name="apply", with_app_command=True, description="Analisa & apply sesuai policy")
    @commands.is_owner()
    async def selfheal_apply(self, ctx: commands.Context):
        set_cfg("SELFHEAL_DM_SUMMARY", True)  # show a summary for manual run
        await ctx.reply("OK. Analisa & apply berjalan.", mention_author=False)
        await self._loop()

async def setup(bot: commands.Bot):
    await bot.add_cog(SelfHealGroqAgent(bot))
