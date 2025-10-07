# -*- coding: utf-8 -*-
"""
Self-heal runtime:
- Exception sentinel via discord.Client._run_event wrapper
- Hotfix registry (signature -> patcher)
- Circuit breaker per signature
- Optional OpenAI summary if OPENAI-KEY / OPENAI_API_KEY available

Safe: tidak menghapus/merusak config JSON.
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
import time
from typing import Callable, Dict, Optional, Tuple

import discord
from discord.ext import commands

LOGGER = logging.getLogger(__name__)

OPENAI_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI-KEY") or ""

# ---- Circuit breaker config ----
CB_WINDOW_SEC = int(os.getenv("SELFHEAL_CB_WINDOW", "120"))  # 2 menit
CB_THRESHOLD  = int(os.getenv("SELFHEAL_CB_THRESHOLD", "5")) # >5 error/2m => breaker
COOLDOWN_SEC  = int(os.getenv("SELFHEAL_COOLDOWN", "300"))   # 5 menit disable

PatchFunc = Callable[[commands.Bot], "PatchResult"]

class PatchResult:
    def __init__(self, applied: bool, note: str = "", reload_ok: Optional[bool] = None):
        self.applied = applied
        self.note = note
        self.reload_ok = reload_ok

def _read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def _write_text(path: str, text: str) -> None:
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)

async def _maybe_send_log(bot: commands.Bot, message: str) -> None:
    LOGGER.warning("[self-heal] %s", message)
    try:
        for guild in bot.guilds:
            chan = guild.system_channel
            if chan and chan.permissions_for(guild.me).send_messages:
                await chan.send(f"⚠️ **Self-Heal:** {message}")
                return
    except Exception:
        pass

def _make_signature_key(exc: BaseException, event_name: str) -> str:
    msg = f"{exc.__class__.__name__}:{str(exc)}"
    return f"{event_name}|{msg[:160]}"

class _CircuitState:
    __slots__ = ("events", "blocked_until")
    def __init__(self):
        self.events: list[float] = []
        self.blocked_until: float = 0.0

    def add(self) -> Tuple[int, bool]:
        now = time.time()
        self.events = [t for t in self.events if now - t <= CB_WINDOW_SEC]
        self.events.append(now)
        tripped = len(self.events) >= CB_THRESHOLD
        if tripped:
            self.blocked_until = now + COOLDOWN_SEC
        return len(self.events), tripped

    def is_blocked(self) -> bool:
        return time.time() < self.blocked_until

def _robust_history_gen_code() -> str:
    return (
        'history = "".join(\n'
        '    f"{(t[1] if len(t)==3 else t[0])}: {(t[2] if len(t)==3 else t[1])}\\n"\n'
        '    for t in past if isinstance(t,(list,tuple)) and len(t)>=2\n'
        ')\n'
    )

def _apply_chat_neurolite_file_patch(src: str) -> Tuple[str, bool]:
    lines = src.splitlines(True)
    changed = False
    for i, line in enumerate(lines):
        if "history" in line and "join(" in line and "content in past" in line and " for _" in line:
            indent = line[:len(line) - len(line.lstrip())]
            new_text = "".join(indent + l for l in _robust_history_gen_code().splitlines(True))
            lines[i] = new_text
            changed = True
            break
    return ("".join(lines), changed)

def patch_chat_neurolite(bot: commands.Bot) -> PatchResult:
    modname = "satpambot.bot.modules.discord_bot.cogs.chat_neurolite"
    try:
        mod = sys.modules.get(modname)
        if mod is None:
            mod = __import__(modname, fromlist=["*"])
        path = getattr(mod, "__file__", None)
        if not path or not path.endswith(".py"):
            return PatchResult(False, f"Module path not found for {modname}")
        src = _read_text(path)
        new_src, changed = _apply_chat_neurolite_file_patch(src)
        if not changed:
            return PatchResult(False, "No matching pattern found; maybe already patched.")
        _write_text(path, new_src)
        try:
            bot.unload_extension(modname)
        except Exception:
            pass
        try:
            bot.load_extension(modname)
            return PatchResult(True, "Patched and reloaded ChatNeuroLite", reload_ok=True)
        except Exception as e:
            return PatchResult(True, f"Patched but reload failed: {e}", reload_ok=False)
    except Exception as e:
        return PatchResult(False, f"Patch error: {e}")

HOTFIXES: Dict[str, PatchFunc] = {
    "chat_neurolite_unpack": patch_chat_neurolite,
}

def match_signature_for_hotfix(exc: BaseException, event_name: str, stack: str) -> Optional[str]:
    s = f"{exc.__class__.__name__}:{exc}"
    if event_name == "on_message" and isinstance(exc, ValueError) and "not enough values to unpack" in str(exc):
        if "chat_neurolite.py" in stack and "content in past" in stack:
            return "chat_neurolite_unpack"
    return None

async def _openai_summary_async(error_text: str) -> Optional[str]:
    if not OPENAI_KEY:
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_KEY)
        prompt = ("Ringkas error berikut (maks 5 poin) dan sarankan perbaikan singkat:"
                  "\n\n" + str(error_text)[:4000])
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a senior reliability engineer."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=200,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        LOGGER.warning("OpenAI summary failed: %s", e)
        return None

def _format_stack_from_exc() -> str:
    import traceback
    return "".join(traceback.format_exc())

class SelfHealRuntime(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._orig_run_event = None
        self._cb: Dict[str, _CircuitState] = {}

    def _cb_state(self, key: str) -> _CircuitState:
        st = self._cb.get(key)
        if st is None:
            st = _CircuitState()
            self._cb[key] = st
        return st

    def _wrap_run_event(self):
        if self._orig_run_event is not None:
            return
        orig = discord.Client._run_event

        async def wrapped(client: discord.Client, coro, *args, **kwargs):
            event_name = getattr(coro, "__name__", "unknown")
            try:
                return await orig(client, coro, *args, **kwargs)
            except Exception as exc:
                stack = _format_stack_from_exc()
                sig_key = _make_signature_key(exc, event_name)
                hotfix_key = match_signature_for_hotfix(exc, event_name, stack)
                st = self._cb_state(sig_key)
                count, tripped = st.add()

                applied_note = ""
                applied_flag = False
                if hotfix_key and not st.is_blocked():
                    patcher = HOTFIXES.get(hotfix_key)
                    if patcher:
                        res = patcher(self.bot)
                        applied_flag = res.applied
                        applied_note = res.note

                msg = f"Event '{event_name}' crashed: {exc} (count {count}/{CB_THRESHOLD})."
                if applied_flag:
                    msg += f" Hotfix[{hotfix_key}] applied: {applied_note}"
                elif hotfix_key:
                    msg += f" Hotfix[{hotfix_key}] NOT applied: {applied_note or 'no-op'}"

                if tripped:
                    msg += f" | Circuit breaker TRIPPED for {COOLDOWN_SEC}s"
                asyncio.create_task(_maybe_send_log(self.bot, msg))

                if OPENAI_KEY:
                    summary_text = f"{msg}\n\nStack:\n{stack[-1200:]}"
                    asyncio.create_task(_openai_summary_async(summary_text))

                if tripped:
                    return None
                raise

        self._orig_run_event = orig
        discord.Client._run_event = wrapped  # type: ignore[attr-defined]
        LOGGER.info("[self-heal] discord.Client._run_event patched")

    def cog_unload(self):
        try:
            if self._orig_run_event is not None:
                discord.Client._run_event = self._orig_run_event  # type: ignore[attr-defined]
                LOGGER.info("[self-heal] _run_event restored")
        except Exception:
            pass

    @commands.Cog.listener()
    async def on_ready(self):
        self._wrap_run_event()
        await _maybe_send_log(self.bot, "SelfHealRuntime aktif")

async def setup(bot: commands.Bot):
    await bot.add_cog(SelfHealRuntime(bot))
