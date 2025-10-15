
from __future__ import annotations
import os, asyncio, logging, json, re
from pathlib import Path
from typing import Optional, Tuple

import discord
from discord import app_commands
from discord.ext import commands

log = logging.getLogger(__name__)

def _strip_relaxed_json(s: str) -> str:
    s = re.sub(r"(?m)//.*?$", "", s)
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    s = re.sub(r",\s*([}\]])", r"\1", s)
    return s

def _load_json_relaxed(p: Path):
    try:
        raw = p.read_text(encoding="utf-8", errors="ignore").lstrip("\ufeff")
        try:
            return json.loads(raw)
        except Exception:
            return json.loads(_strip_relaxed_json(raw))
    except Exception:
        return None

def _repo_root() -> Path:
    cwd = Path.cwd()
    for parent in [cwd] + list(cwd.parents):
        if (parent / ".git").exists():
            return parent
    return cwd

def cfg_resilient(key: str, default: Optional[str] = None):
    v = os.getenv(key)
    if v:
        return v
    try:
        from satpambot.config.runtime import cfg as _cfg  # type: ignore
        val = _cfg(key)
        if val is not None:
            return val
    except Exception:
        pass
    root = _repo_root()
    candidates = [
        os.getenv("SATPAMBOT_CONFIG") or "",
        "satpambot_config.local.json",
        "config/satpambot_config.local.json",
        "config.json",
        "satpambot_config.json",
        "settings.local.json",
    ]
    seen = set()
    for rel in candidates:
        if not rel:
            continue
        p = Path(rel)
        if not p.is_absolute():
            p = root / rel
        if p in seen or not p.exists():
            continue
        seen.add(p)
        data = _load_json_relaxed(p)
        if isinstance(data, dict):
            if key in data and data[key]:
                return data[key]
            for k,v2 in data.items():
                if isinstance(k,str) and k.lower()==key.lower() and v2:
                    return v2
    return default

PROVIDER_GEMINI = "gemini"
PROVIDER_GROQ = "groq"

class ProviderRouter:
    def __init__(self):
        self.provider_pref = (cfg_resilient("QNA_PROVIDER", "auto") or "auto").lower()
        try:
            self.max_tokens = int(cfg_resilient("QNA_MAX_TOKENS", "512") or "512")
        except Exception:
            self.max_tokens = 512
        try:
            self.temperature = float(cfg_resilient("QNA_TEMPERATURE", "0.3") or "0.3")
        except Exception:
            self.temperature = 0.3

    def _have_gemini(self) -> bool:
        if not (cfg_resilient("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")):
            return False
        try:
            import importlib
            importlib.import_module("google.generativeai")
            return True
        except Exception:
            return False

    def _have_groq(self) -> bool:
        if not (cfg_resilient("GROQ_API_KEY") or os.getenv("GROQ_API_KEY")):
            return False
        try:
            import importlib
            importlib.import_module("groq")
            return True
        except Exception:
            return False

    def choose(self) -> Tuple[str, Optional[str]]:
        pref = self.provider_pref
        if pref == PROVIDER_GEMINI:
            if self._have_gemini():
                return PROVIDER_GEMINI, None
            return "", "GEMINI_API_KEY/GOOGLE_API_KEY not set or SDK missing"
        if pref == PROVIDER_GROQ:
            if self._have_groq():
                return PROVIDER_GROQ, None
            return "", "GROQ_API_KEY not set or SDK missing"
        if self._have_gemini():
            return PROVIDER_GEMINI, None
        if self._have_groq():
            return PROVIDER_GROQ, None
        return "", "No provider available"

    async def complete(self, prompt: str, system: Optional[str] = None) -> str:
        provider, err = self.choose()
        if not provider:
            raise RuntimeError(err or "No provider available")
        if provider == PROVIDER_GEMINI:
            try:
                return await self._complete_gemini(prompt, system)
            except Exception as e:
                # Auto-fallback for common Gemini errors
                try:
                    from google.api_core.exceptions import NotFound, PermissionDenied
                    if isinstance(e, (NotFound, PermissionDenied)) and self._have_groq():
                        return await self._complete_groq(prompt, system)
                except Exception:
                    pass
                raise
        if provider == PROVIDER_GROQ:
            return await self._complete_groq(prompt, system)
        raise RuntimeError("Unknown provider")

    async def _complete_gemini(self, prompt: str, system: Optional[str]) -> str:
        model_name = cfg_resilient("QNA_MODEL_GEMINI", "gemini-flash-latest") or "gemini-flash-latest"
        api_key = cfg_resilient("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY/GOOGLE_API_KEY is not set")
        try:
            import google.generativeai as genai  # type: ignore
        except Exception:
            raise RuntimeError("google-generativeai SDK is not installed. pip install google-generativeai")
        genai.configure(api_key=api_key)
        def _call():
            generation_config = {"temperature": self.temperature, "max_output_tokens": self.max_tokens}
            model = genai.GenerativeModel(model_name, generation_config=generation_config)
            parts = []
            if system: parts.append(f"System: {system}")
            parts.append(f"User: {prompt}")
            resp = model.generate_content(parts)
            text = getattr(resp, "text", None)
            if not text and getattr(resp, "candidates", None):
                try: text = resp.candidates[0].content.parts[0].text
                except Exception: text = None
            if not text:
                raise RuntimeError("Empty completion from Gemini")
            return text.strip()
        return await asyncio.get_event_loop().run_in_executor(None, _call)

    async def _complete_groq(self, prompt: str, system: Optional[str]) -> str:
        model = cfg_resilient("QNA_MODEL_GROQ", "llama-3.1-8b-instant") or "llama-3.1-8b-instant"
        api_key = cfg_resilient("GROQ_API_KEY") or os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("GROQ_API_KEY is not set")
        try:
            from groq import Groq  # type: ignore
        except Exception:
            raise RuntimeError("groq SDK is not installed. pip install groq")
        client = Groq(api_key=api_key)
        msgs = []
        if system: msgs.append({"role": "system", "content": system})
        msgs.append({"role": "user", "content": prompt})
        for attempt in range(3):
            try:
                resp = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: client.chat.completions.create(
                        model=model, messages=msgs,
                        temperature=self.temperature, max_tokens=self.max_tokens,
                    )
                )
                text = (resp.choices[0].message.content or "").strip()
                if text: return text
                raise RuntimeError("Empty completion")
            except Exception:
                if attempt == 2: raise
                await asyncio.sleep(0.8 * (attempt + 1))

class QnaDualProvider(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.router = ProviderRouter()
        log.info("[qna] initialized (provider_pref=%s)", self.router.provider_pref)

    @app_commands.command(name="qna", description="Tanya cepat ke LLM (Gemini/Groq).")
    @app_commands.describe(prompt="Pertanyaan kamu")
    async def qna(self, interaction: discord.Interaction, prompt: str):
        try:
            await interaction.response.defer(ephemeral=True, thinking=True)
        except Exception:
            pass
        if (cfg_resilient("QNA_EPHEMERAL_DEFAULT", "1") or "1").strip() != "1":
            ephemeral = False
        else:
            ephemeral = True
        system = "You are SatpamBot's QnA assistant. Jawab singkat dan praktis."
        try:
            text = await self.router.complete(prompt, system=system)
        except Exception as e:
            log.exception("qna error: %s", e)
            hint = "Set GEMINI_API_KEY / GROQ_API_KEY di satpambot_config.local.json atau ENV. QNA_PROVIDER=gemini|groq|auto."
            return await interaction.followup.send(f"Gagal mendapatkan jawaban: `{e}`\n{hint}", ephemeral=ephemeral)
        await interaction.followup.send(text or "_(tidak ada jawaban)_", ephemeral=ephemeral)

async def setup(bot: commands.Bot):
    await bot.add_cog(QnaDualProvider(bot))

def setup(bot: commands.Bot):
    try:
        bot.add_cog(QnaDualProvider(bot))
    except TypeError:
        pass
