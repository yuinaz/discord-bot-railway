
# a06_selfheal_autoexec_overlay.py (v6.2)
# Autonomous self-heal overlay that, after applying fixes, uses existing in-bot
# repo pull & restart mechanisms (no Render API required).
#
# Import-safe: all optional deps guarded; never raise during import/setup.

import os, re, json, asyncio, logging, shlex, subprocess, sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from discord.ext import commands

logger = logging.getLogger(__name__)

def _env(k, default=None):
    v = os.getenv(k, default)
    if isinstance(v, str):
        return v.strip()
    return v

try:
    REPO_DIR = Path(_env("CWD", "/opt/render/project/src"))
except Exception:
    REPO_DIR = Path("/opt/render/project/src")

GITHUB_REPO = _env("GITHUB_REPO")
GITHUB_BRANCH = _env("GITHUB_BRANCH", "main")
GITHUB_TOKEN = _env("GITHUB_TOKEN")
USE_GIT = _env("SELFHEAL_USE_GIT", "1") == "1"

GROQ_API_KEY = _env("GROQ_API_KEY")
GOOGLE_API_KEY = _env("GOOGLE_API_KEY")

# ----------------- JSON edits parser -----------------
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
        # fallback: code block w/ path=...
        path_m = re.search(r"path\s*=\s*([^\n`]+)", text)
        code_m = re.search(r"```(?:python|py|)([\s\S]*?)```", text)
        if path_m and code_m:
            return {"edits":[{"path":path_m.group(1).strip(), "type":"replace", "content":code_m.group(1)}]}
    except Exception:
        return None
    return None

# ----------------- LLM callers (optional) -----------------
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
            cand = None
            try:
                cand = data["candidates"][0]["content"]["parts"][0]["text"]
            except Exception:
                cand = None
            return cand
    except Exception as e:
        logger.info("[selfheal] gemini failed: %r", e)
        return None

# ----------------- Apply edits & repo ops -----------------
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
        if GITHUB_TOKEN and GITHUB_REPO:
            remote = f"https://{GITHUB_TOKEN}@github.com/{GITHUB_REPO}.git"
            res = run(f"git push {remote} HEAD:{GITHUB_BRANCH}", check=False)
            return res.returncode == 0
        res = run(f"git push origin HEAD:{GITHUB_BRANCH}", check=False)
        return res.returncode == 0
    except Exception as e:
        logger.info("[selfheal:git] push failed: %r", e)
        return False

async def _restart_via_existing_cogs(bot) -> bool:
    # Try known cogs/methods commonly seen in your repo
    # 1) repo_pull_and_restart cog
    for cog_name in ("repo_pull_and_restart","repo_restart_hook","repo_restart","repo_pull"):
        cog = bot.get_cog(cog_name)
        if not cog:
            continue
        for m in ("pull_and_restart","restart","pullrepo","pull_and_reboot","pull","do_restart"):
            fn = getattr(cog, m, None)
            if fn:
                try:
                    res = fn()
                    if asyncio.iscoroutine(res):
                        await res
                    logger.info("[selfheal:restart] used %s.%s()", cog_name, m)
                    return True
                except Exception as e:
                    logger.info("[selfheal:restart] %s.%s failed: %r", cog_name, m, e)
    return False

def _restart_local_process():
    # Fallback: do a git pull (best-effort) then exit to let platform restart
    try:
        subprocess.run(["git","pull"], cwd=str(REPO_DIR), capture_output=True, text=True)
    except Exception:
        pass
    logger.info("[selfheal:restart] exiting process for restart")
    os._exit(0)

async def _llm_fix(bot, prompt: str) -> Tuple[bool,str]:
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
    # Always try in-bot restart flow first
    used_cog = await _restart_via_existing_cogs(bot)
    if not used_cog:
        _restart_local_process()
    return (True, f"changed={len(changed)} pushed={pushed} restart={'cog' if used_cog else 'process'}")

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
            ok, info = await _llm_fix(self.bot, prefix + text[:4000])
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
    try:
        await bot.add_cog(SelfHealAutoExec(bot))
    except Exception as e:
        logger.info("[selfheal:autoexec] setup failed but swallowed: %r", e)
