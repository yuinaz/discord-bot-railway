
from discord.ext import commands
import asyncio, json, logging, os, re, inspect, importlib, time
from typing import Optional, Dict, Any, Tuple
import httpx

from urllib.parse import quote as _q

LOG = logging.getLogger(__name__)

# === Config (ENV) ===
ENABLE = os.getenv("SELFHEAL_QUORUM_ENABLE", "1") == "1"
TIMEOUT = float(os.getenv("SELFHEAL_QUORUM_TIMEOUT_S", "15"))
BLOCK_ACTIONS = set([s.strip().lower() for s in os.getenv("SELFHEAL_BLOCK_ACTIONS", "restart,redeploy,reexec,reload").split(",") if s.strip()])
MIN_SCORE = int(os.getenv("SELFHEAL_MIN_APPROVAL_SCORE", "90"))
REQUIRE_BOTH = os.getenv("SELFHEAL_REQUIRE_BOTH", "1") == "1"
LOG_CHANNEL_ID = int(os.getenv("SELFHEAL_LOG_CHANNEL_ID", "0"))

# Rate limit
RL_WINDOW_SECONDS = int(os.getenv("SELFHEAL_RL_WINDOW_SECONDS", "1800"))   # 30 min
RL_MAX_PER_DAY = int(os.getenv("SELFHEAL_RL_MAX_PER_DAY", "3"))
RL_TZ = os.getenv("SELFHEAL_RL_TZ", "Asia/Jakarta")

# Storage
UPSTASH_URL = os.getenv("UPSTASH_REDIS_REST_URL")
UPSTASH_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN")
DATA_DIR = os.getenv("DATA_DIR", "data/runtime")
os.makedirs(DATA_DIR, exist_ok=True)

# === Helpers: tolerant JSON ===
def _extract_json_block(text: str) -> Optional[str]:
    if not text: return None
    m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.I)
    if m: return m.group(1).strip()
    start = text.find("{")
    if start == -1: return None
    depth = 0
    for i, ch in enumerate(text[start:], start=start):
        if ch == "{": depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0: return text[start:i+1]
    return None

def _sanitize_json_like(s: str) -> str:
    s = re.sub(r"\b'([A-Za-z0-9_\-]+)'\s*:", r'"\1":', s)
    s = re.sub(r':\s*\'([^\'\\]*(?:\\.[^\'\\]*)*)\'', lambda m: ':"%s"' % m.group(1).replace('"','\\"'), s)
    s = re.sub(r",\s*(?=[}\]])", "", s)
    s = re.sub(r"\bTrue\b", "true", s); s = re.sub(r"\bFalse\b", "false", s); s = re.sub(r"\bNone\b", "null", s)
    return s

def parse_json_tolerant(text: str) -> Optional[dict]:
    if not text: return None
    for candidate in (text, _extract_json_block(text) or text):
        try:
            return json.loads(candidate)
        except Exception:
            pass
        try:
            return json.loads(_sanitize_json_like(candidate))
        except Exception:
            pass
    return None

# === Time helpers ===
def _now_ts() -> int:
    return int(time.time())

def _date_str_local(ts: Optional[int] = None) -> str:
    ts = ts or _now_ts()
    try:
        from zoneinfo import ZoneInfo
        import datetime as _dt
        dt = _dt.datetime.fromtimestamp(ts, ZoneInfo(RL_TZ))
        return dt.strftime("%Y-%m-%d")
    except Exception:
        # fallback UTC date
        return time.strftime("%Y-%m-%d", time.gmtime(ts))

# === Upstash helpers (best-effort) ===
async def _upstash_get(cli: httpx.AsyncClient, key: str) -> Optional[str]:
    if not (UPSTASH_URL and UPSTASH_TOKEN): return None
    try:
        r = await cli.get(f"{UPSTASH_URL}/get/{_q(key, safe='')}", headers={"Authorization": f"Bearer {UPSTASH_TOKEN}"})
        if r.status_code == 200:
            return (r.json() or {}).get("result")
    except Exception: pass
    return None

async def _upstash_set(cli: httpx.AsyncClient, key: str, value: str) -> bool:
    if not (UPSTASH_URL and UPSTASH_TOKEN): return False
    try:
        r = await cli.post(f"{UPSTASH_URL}/set/{_q(key,safe='')}/{_q(value,safe='')}", headers={"Authorization": f"Bearer {UPSTASH_TOKEN}"})
        return r.status_code == 200
    except Exception: return False

async def _upstash_incr(cli: httpx.AsyncClient, key: str) -> Optional[int]:
    if not (UPSTASH_URL and UPSTASH_TOKEN): return None
    try:
        r = await cli.post(f"{UPSTASH_URL}/incr/{_q(key,safe='')}", headers={"Authorization": f"Bearer {UPSTASH_TOKEN}"})
        if r.status_code == 200:
            return int((r.json() or {}).get("result", 0))
    except Exception: pass
    return None

async def _upstash_expire(cli: httpx.AsyncClient, key: str, seconds: int) -> bool:
    if not (UPSTASH_URL and UPSTASH_TOKEN): return False
    try:
        r = await cli.post(f"{UPSTASH_URL}/expire/{_q(key,safe='')}/{seconds}", headers={"Authorization": f"Bearer {UPSTASH_TOKEN}"})
        return r.status_code == 200
    except Exception: return False

# === Local file fallback ===
_rl_file = os.path.join(DATA_DIR, "selfheal_rl.json")
def _load_rl() -> dict:
    try:
        with open(_rl_file, "r", encoding="utf-8") as f: return json.load(f)
    except Exception: return {"last_ts": 0, "daily": {}}

def _save_rl(obj: dict):
    try:
        tmp = _rl_file + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f: json.dump(obj, f, ensure_ascii=False, indent=2)
        os.replace(tmp, _rl_file)
    except Exception: pass

# === Rate limit check ===
async def rate_limit_allow(risky_action: bool) -> Tuple[bool, str]:
    if not risky_action: return True, "not risky"
    now = _now_ts()
    date_key = _date_str_local(now)
    # Try Upstash first
    async with httpx.AsyncClient(timeout=TIMEOUT) as cli:
        # cooldown
        last_ts = None
        s = await _upstash_get(cli, "selfheal:last_risky_ts")
        if s is not None:
            try: last_ts = int(s)
            except Exception: last_ts = None
        if last_ts is not None and (now - last_ts) < RL_WINDOW_SECONDS:
            return False, f"cooldown {RL_WINDOW_SECONDS - (now - last_ts)}s remaining"

        # daily count
        daily_key = f"selfheal:restart_count:{date_key}"
        cnt_res = await _upstash_incr(cli, daily_key)
        if cnt_res is not None:
            # set expiry to end-of-day (~ 26 hours to be safe)
            await _upstash_expire(cli, daily_key, 26*3600)
            if cnt_res > RL_MAX_PER_DAY:
                return False, f"daily limit exceeded ({cnt_res}>{RL_MAX_PER_DAY})"

            # record last_ts
            await _upstash_set(cli, "selfheal:last_risky_ts", str(now))
            return True, f"ok (count={cnt_res})"

    # Fallback local
    rl = _load_rl()
    last_ts = int(rl.get("last_ts", 0) or 0)
    if last_ts and (now - last_ts) < RL_WINDOW_SECONDS:
        return False, f"cooldown {RL_WINDOW_SECONDS - (now - last_ts)}s remaining"
    daily = rl.setdefault("daily", {})
    cnt = int(daily.get(date_key, 0)) + 1
    if cnt > RL_MAX_PER_DAY:
        return False, f"daily limit exceeded ({cnt}>{RL_MAX_PER_DAY})"
    daily[date_key] = cnt
    rl["last_ts"] = now
    _save_rl(rl)
    return True, f"ok (count={cnt})"

# === Preflight (same as before, trimmed) ===
def _check_file_json(path: str):
    if not path: return False, "path empty", None
    try:
        with open(path, "r", encoding="utf-8") as f: raw = f.read()
        return True, "ok", json.loads(raw)
    except FileNotFoundError:
        return False, f"not found: {path}", None
    except Exception as e:
        return False, f"invalid json: {e!r}", None

def preflight(bot) -> dict:
    out = {"ok": True, "issues": [], "checks": {}}
    ov_path = os.getenv("CONFIG_OVERRIDES_PATH") or "data/config/overrides.render-free.json"
    ok, note, _ = _check_file_json(ov_path) if os.path.exists(ov_path) else (True, "skip (missing is allowed)", None)
    out["checks"]["overrides_json"] = {"path": ov_path, "ok": ok, "note": note}
    if not ok: out["ok"] = False; out["issues"].append(f"overrides_json: {note}")

    ladder_path = os.getenv("LADDER_JSON_PATH") or "data/neuro-lite/ladder.json"
    ok, note, ladder = _check_file_json(ladder_path)
    out["checks"]["ladder_json"] = {"path": ladder_path, "ok": ok, "note": note, "keys": list((ladder or {}).keys())[:6]}
    if not ok: out["ok"] = False; out["issues"].append(f"ladder_json: {note}")

    try:
        mod = importlib.import_module("satpambot.bot.modules.discord_bot.cogs.learning_passive_observer")
        src = ""
        try:
            import inspect as _ins; src = _ins.getsource(mod)
        except Exception: pass
        has_utils = "ladder_utils" in src
    except Exception:
        has_utils = False
    out["checks"]["learning_passive_observer"] = {"has_ladder_utils": has_utils}
    if not has_utils: out["ok"] = False; out["issues"].append("learning_passive_observer: ladder_utils missing")

    has_xp_add = hasattr(bot, "xp_add") and callable(getattr(bot, "xp_add"))
    out["checks"]["xp_direct_method"] = {"has_xp_add": has_xp_add}
    if not has_xp_add: out["ok"] = False; out["issues"].append("xp_direct_method: missing bot.xp_add()")

    safe_ok = False
    try:
        m = importlib.import_module("satpambot.bot.modules.discord_bot.helpers.embed_scribe")
        upsert = getattr(getattr(m, "EmbedScribe", object), "upsert", None)
        safe_ok = inspect.iscoroutinefunction(upsert) or getattr(upsert, "__safeawait_patched__", False)
    except Exception: safe_ok = False
    out["checks"]["progress_embed_safeawait"] = {"ok": safe_ok}
    if not safe_ok: out["ok"] = False; out["issues"].append("progress_embed: upsert not awaitable/ not patched")

    out["checks"]["providers"] = {"groq_key": bool(os.getenv("GROQ_API_KEY")), "gemini_key": bool(os.getenv("GOOGLE_API_KEY"))}
    return out

# === Reviewers ===
async def ask_groq(prompt: str) -> Tuple[int, str]:
    key = os.getenv("GROQ_API_KEY"); 
    if not key: return 0, "GROQ_API_KEY missing"
    url = os.getenv("GROQ_API_BASE", "https://api.groq.com/openai/v1/chat/completions")
    model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as cli:
            r = await cli.post(url, headers={"Authorization": f"Bearer {key}"}, json={
                "model": model,
                "messages": [
                    {"role": "system", "content": "Return STRICT JSON {\"approve\":bool, \"score\":0..100, \"issues\":[string], \"reason\":string}. Approve ONLY if all preflight checks pass AND plan is necessary."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0
            })
            r.raise_for_status()
            txt = r.json()["choices"][0]["message"]["content"]
            obj = parse_json_tolerant(txt) or {}
            score = int(obj.get("score", 0)); approve = bool(obj.get("approve", False))
            if not approve: score = min(score, 0)
            return score, (obj.get("reason","")[:280] or "")
    except Exception as e:
        return 0, f"groq_err:{e!r}"

async def ask_gemini(prompt: str) -> Tuple[int, str]:
    key = os.getenv("GOOGLE_API_KEY")
    if not key: return 0, "GOOGLE_API_KEY missing"
    model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as cli:
            r = await cli.post(url, json={
                "contents": [{"parts": [{"text": "Balas HANYA JSON {\"approve\":bool, \"score\":0..100, \"issues\":[string], \"reason\":string}. Setujui HANYA jika semua preflight PASS dan rencana diperlukan.\n" + prompt}]}]
            })
            r.raise_for_status()
            txt = r.json().get("candidates",[{}])[0].get("content",{}).get("parts",[{"text":""}])[0].get("text","")
            obj = parse_json_tolerant(txt) or {}
            score = int(obj.get("score", 0)); approve = bool(obj.get("approve", False))
            if not approve: score = min(score, 0)
            return score, (obj.get("reason","")[:280] or "")
    except Exception as e:
        return 0, f"gemini_err:{e!r}"

def build_prompt(plan: Dict[str, Any], pf: dict) -> str:
    return (
        "Review rencana SELF-HEAL berikut dan hasil PRE-FLIGHT (checks & issues). "
        "Setujui HANYA jika semua checks PASS dan rencana diperlukan untuk mengatasi error "
        "dengan peluang keberhasilan tinggi dan minim risiko loop.\n"
        f"Plan: {json.dumps(plan, ensure_ascii=False)}\n"
        f"Preflight: {json.dumps(pf, ensure_ascii=False)}"
    )

async def quorum_decide(bot, plan: Dict[str, Any]) -> Tuple[bool, str]:
    actions = [str(a).lower() for a in (plan.get("actions") or [])]
    risky = any(a in BLOCK_ACTIONS for a in actions)
    if not ENABLE or not risky:
        return True, "not gated"

    # Rate limit FIRST
    rl_ok, rl_note = await rate_limit_allow(risky)
    if not rl_ok:
        return False, f"rate-limit: {rl_note}"

    pf = preflight(bot)
    if not pf.get("ok"):
        return False, f"preflight failed: {pf.get('issues')}"

    prompt = build_prompt(plan, pf)
    groq_task = asyncio.create_task(ask_groq(prompt))
    gm_task = asyncio.create_task(ask_gemini(prompt))
    groq_score, groq_note = await groq_task
    gem_score,  gem_note  = await gm_task
    groq_ok = groq_score >= MIN_SCORE
    gem_ok  = gem_score  >= MIN_SCORE
    overall = (groq_ok and gem_ok) if REQUIRE_BOTH else (groq_ok or gem_ok)
    note = f"groq:{groq_score} ({groq_note}) | gemini:{gem_score} ({gem_note}) | min={MIN_SCORE}, both={REQUIRE_BOTH}"
    return overall, note

class SelfHealQuorumV2(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        try:
            import satpambot.bot.modules.discord_bot.cogs.selfheal_groq_agent as T
        except Exception as e:
            LOG.warning("[quorum-v2] import fail: %r", e); return
        Cog = getattr(T, "SelfHealGroqAgent", None) or getattr(T, "SelfHealRuntime", None)
        if not Cog: 
            LOG.warning("[quorum-v2] target class missing"); return
        target_name = "_execute_plan" if hasattr(Cog, "_execute_plan") else "_apply_plan" if hasattr(Cog, "_apply_plan") else None
        if not target_name:
            LOG.warning("[quorum-v2] no executable method to wrap"); return
        orig = getattr(Cog, target_name)
        if getattr(orig, "__quorum_v2_rl__", False): return

        async def wrapped(self, plan: Dict[str, Any]):
            ok, note = await quorum_decide(self.bot, plan)
            if not ok:
                LOG.warning("[quorum-v2] BLOCKED plan %s | %s", plan, note)
                if LOG_CHANNEL_ID:
                    ch = self.bot.get_channel(LOG_CHANNEL_ID)
                    if ch:
                        try:
                            await ch.send(f"⛔ Self-heal diblokir: {note}\n```json\n{json.dumps(plan, ensure_ascii=False)}\n```")
                        except Exception: pass
                return
            LOG.info("[quorum-v2] APPROVED: %s", note)
            return await orig(self, plan)

        setattr(wrapped, "__quorum_v2_rl__", True)
        setattr(Cog, target_name, wrapped)
        LOG.info("[quorum-v2] wrapped %s.%s (rate-limit + quorum)", Cog.__name__, target_name)
async def setup(bot):
    await bot.add_cog(SelfHealQuorumV2(bot))
    print("[quorum-v2] overlay loaded — rate-limit + quorum (≥90 both)")