
# a06_selfheal_autoexec_overlay.py (v6.1)
# Import-safe, dependency-light autonomous self-heal overlay.
# - Guards all optional deps inside functions
# - Never raises on import/setup; degrades to no-op with INFO logs

import os, re, json, asyncio, logging, shlex, subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from discord.ext import commands

logger = logging.getLogger(__name__)

def _env(k, default=None):
    v = os.getenv(k, default)
    if isinstance(v, str):
        return v.strip()
    return v

# Resolve repo dir safely
try:
    REPO_DIR = Path(_env("CWD", "/opt/render/project/src"))
except Exception:
    REPO_DIR = Path("/opt/render/project/src")

GITHUB_REPO = _env("GITHUB_REPO")  # "owner/name"
GITHUB_BRANCH = _env("GITHUB_BRANCH", "main")
GITHUB_TOKEN = _env("GITHUB_TOKEN")
RENDER_API_KEY = _env("RENDER_API_KEY")
RENDER_SERVICE_ID = _env("RENDER_SERVICE_ID")
USE_GIT = _env("SELFHEAL_USE_GIT", "1") == "1"

GROQ_API_KEY = _env("GROQ_API_KEY")
GOOGLE_API_KEY = _env("GOOGLE_API_KEY")

def _extract_edits(text: str) -> Optional[Dict[str, Any]]:
    try:
        m = re.search(r"\{(?:.|\n)*\}", text)
        cand = None
        if m:
            try:
                cand = json.loads(m.group(0))
            except Exception:
                cand = None
        if isinstance(cand, dict) and "edits" in cand:
            return cand
        path_m = re.search(r"path\s*=\s*([^\n`]+)", text)
        code_m = re.search(r"```(?:python|py|)([\s\S]*?)```", text)
        if path_m and code_m:
            return {"edits":[{"path":path_m.group(1).strip(), "type":"replace", "content":code_m.group(1)}]}
    except Exception:
        return None
    return None

async def _call_groq(prompt: str) -> Optional[str]:
    if not GROQ_API_KEY:
        return None
    try:
        import httpx
    except Exception:
        logger.info("[selfheal] httpx not available for Groq")
        return None
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
        body = {
            "model": _env("SELFHEAL_GROQ_MODEL","llama-3.1-70b-versatile"),
            "messages": [
                {"role":"system","content":"You fix Python Discord bot modules. Return JSON with file edits: {\"edits\":[{\"path\":\"...\",\"type\":\"replace\",\"content\":\"<full file>\"}]}"},
                {"role":"user","content": prompt}
            ],
            "temperature": 0.2,
        }
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(url, headers=headers, json=body)
            r.raise_for_status()
            data = r.json()
            return data.get("choices",[{}])[0].get("message",{}).get("content")
    except Exception as e:
        logger.info("[selfheal] groq failed: %r", e)
        return None

async def _call_gemini(prompt: str) -> Optional[str]:
    if not GOOGLE_API_KEY:
        return None
    try:
        import httpx
    except Exception:
        return None
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GOOGLE_API_KEY}"
        body = {"contents":[{"parts":[{"text": "You fix Python Discord bot modules. Return pure JSON with file edits as described earlier."},{"text": prompt}]}]}
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(url, json=body)
            r.raise_for_status()
            data = r.json()
            # Be defensive: walk safely
            cand = None
            try:
                cand = data["candidates"][0]["content"]["parts"][0]["text"]
            except Exception:
                cand = None
            return cand
    except Exception as e:
        logger.info("[selfheal] gemini failed: %r", e)
        return None

def _apply_edits(edits: Dict[str,Any]) -> List[str]:
    changed: List[str] = []
    try:
        for e in edits.get("edits", []):
            p = REPO_DIR / e.get("path","").strip("/")
            p.parent.mkdir(parents=True, exist_ok=True)
            content = str(e.get("content",""))
            p.write_text(content, encoding="utf-8")
            changed.append(str(p))
    except Exception as e:
        logger.info("[selfheal] applying edits failed: %r", e)
    return changed

def _git_push(changed_files: List[str]) -> bool:
    if not USE_GIT:
        return False
    try:
        def run(cmd, check=True):
            logger.info("[selfheal:git] %s", cmd)
            res = subprocess.run(shlex.split(cmd), cwd=str(REPO_DIR), capture_output=True, text=True)
            if check and res.returncode != 0:
                logger.info("[selfheal:git] failed: %s", res.stderr[:400])
            return res
        run("git config user.email bot@localhost", check=False)
        run("git config user.name SelfHealBot", check=False)
        run(f"git checkout -B {GITHUB_BRANCH}", check=False)
        run("git add -A", check=False)
        msg = "selfheal: auto-fix via LLM"
        run(f"git commit -m {shlex.quote(msg)}", check=False)
        # Prefer HTTPS with token if provided
        if GITHUB_TOKEN and GITHUB_REPO:
            remote = f"https://{GITHUB_TOKEN}@github.com/{GITHUB_REPO}.git"
            res = run(f"git push {remote} HEAD:{GITHUB_BRANCH}", check=False)
            return res.returncode == 0
        # else try default origin
        res = run(f"git push origin HEAD:{GITHUB_BRANCH}", check=False)
        return res.returncode == 0
    except Exception as e:
        logger.info("[selfheal:git] push failed: %r", e)
        return False

async def _render_deploy():
    if not (RENDER_API_KEY and RENDER_SERVICE_ID):
        return False
    try:
        import httpx
    except Exception:
        return False
    try:
        url = f"https://api.render.com/v1/services/{RENDER_SERVICE_ID}/deploys"
        headers = {"Authorization": f"Bearer {RENDER_API_KEY}"}
        payload = {"clearCache": True}
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(url, headers=headers, json=payload)
            ok = r.status_code in (200,201)
            logger.info("[selfheal:render] trigger deploy -> %s (%s)", r.status_code, r.text[:200])
            return ok
    except Exception as e:
        logger.info("[selfheal:render] deploy failed: %r", e)
        return False

async def _llm_fix(prompt: str) -> Tuple[bool,str]:
    text = await _call_groq(prompt) or await _call_gemini(prompt)
    if not text:
        return (False,"no-llm-response")
    edits = _extract_edits(text)
    if not edits:
        return (False,"no-edits-parsed")
    changed = _apply_edits(edits)
    if not changed:
        return (False,"no-files-changed")
    pushed = _git_push(changed)
    await _render_deploy()
    return (True, f"changed={len(changed)} pushed={pushed}")

class SelfHealAutoExec(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.busy = False

    async def _handle_error(self, text: str):
        if self.busy:
            return
        self.busy = True
        try:
            prefix = "Make minimal edits to eliminate error/warnings. Return JSON {\"edits\":[{\"path\":\"...\",\"type\":\"replace\",\"content\":\"...\"}]}\n"
            ok, info = await _llm_fix(prefix + text[:4000])
            logger.info("[selfheal:autoexec] result: %s (%s)", ok, info)
        finally:
            self.busy = False

    @commands.Cog.listener()
    async def on_error(self, event_method, *args, **kwargs):
        try:
            await self._handle_error(f"on_error({event_method}): args={str(args)[:400]} kwargs={str(kwargs)[:400]}")
        except Exception as e:
            logger.info("[selfheal:autoexec] on_error handler failed: %r", e)

    @commands.Cog.listener()
    async def on_selfheal_proposal(self, *args, **kwargs):
        try:
            for it in (*args, *kwargs.values()):
                if hasattr(it, "execute"):
                    res = it.execute(approve=True)
                    if asyncio.iscoroutine(res):
                        await res
                    logger.info("[selfheal:autoexec] auto-approved & executed proposal")
                    return
            await self._handle_error(f"proposal: {args} {kwargs}")
        except Exception as e:
            logger.info("[selfheal:autoexec] proposal handler failed: %r", e)

    @commands.Cog.listener()
    async def on_exception(self, *args, **kwargs):
        try:
            await self._handle_error(f"exception: {args} {kwargs}")
        except Exception as e:
            logger.info("[selfheal:autoexec] on_exception handler failed: %r", e)

async def setup(bot):
    # Never raise during setup
    try:
        await bot.add_cog(SelfHealAutoExec(bot))
    except Exception as e:
        logger.info("[selfheal:autoexec] setup failed but swallowed: %r", e)
