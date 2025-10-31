from __future__ import annotations
import asyncio, json, logging, os, re
from typing import Any, Dict, Optional, Tuple, List
try:
    import discord
    from discord.ext import commands
except Exception as _e:
    discord = None  # type: ignore
    commands = None  # type: ignore
    _IMPORT_ERR = _e
else:
    _IMPORT_ERR = None

log = logging.getLogger(__name__)

ENABLE = os.getenv("LEINA_XP_STATUS_ENABLE", "1") == "1"
INTERVAL = int(os.getenv("LEINA_XP_STATUS_INTERVAL_SEC", "1800"))
STRICT_EDIT_ONLY = os.getenv("XP_MIRROR_STRICT_EDIT", "1") == "1"

PIN_CH_ID = int(os.getenv("XP_PIN_CHANNEL_ID", "0") or 0)
PIN_MSG_ID = int(os.getenv("XP_PIN_MESSAGE_ID", "0") or 0)
PIN_TARGETS_STR = os.getenv("XP_PIN_TARGETS", "").strip()

UPSTASH_URL = os.getenv("UPSTASH_REDIS_REST_URL", "").strip()
UPSTASH_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN", "").strip()
LADDER_FILE = os.getenv("LADDER_FILE", "data/neuro-lite/ladder.json")
XP_SEED_FILE = os.getenv("XP_SEED_FILE", "data/cache/xp_local_seed.json")
XP_SEED_ENV = os.getenv("XP_SENIOR_TOTAL_SEED") or os.getenv("XP_TOTAL_SEED") or ""

def _q_i(v, d=0):
    try: return int(v)
    except Exception:
        try: return int(float(v))
        except Exception: return d

def _targets() -> List[Tuple[int,int]]:
    t: List[Tuple[int,int]] = []
    if PIN_CH_ID and PIN_MSG_ID:
        t.append((PIN_CH_ID, PIN_MSG_ID))
    if PIN_TARGETS_STR:
        for part in re.split(r"[;,\\s]+", PIN_TARGETS_STR):
            if not part: continue
            if ":" in part:
                ch, ms = part.split(":", 1)
                ch = re.sub(r"[^0-9]", "", ch); ms = re.sub(r"[^0-9]", "", ms)
                if ch and ms:
                    try: t.append((int(ch), int(ms)))
                    except Exception: pass
    # dedupe
    seen=set(); uniq=[]
    for p in t:
        if p not in seen:
            uniq.append(p); seen.add(p)
    return uniq

def _load_ladder() -> Dict[str, Any]:
    try:
        with open(LADDER_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log.warning("[leina:xp_status] ladder load failed: %r", e)
        return {
            "senior": {
                "KULIAH": {
                    "S1": 19000, "S2": 35000, "S3": 58000, "S4": 70000, "S5": 96500,
                    "S6": 158000, "S7": 220000, "S8": 262500
                }
            }
        }

def _bands(ladder) -> List[Tuple[str,int,int]]:
    try:
        kv = ladder["senior"]["KULIAH"]
        items = []
        for k, v in kv.items():
            if isinstance(k, str) and k.upper().startswith("S"):
                try:
                    idx = int(k[1:]); req = _q_i(v, None)
                    if req is not None:
                        items.append((idx, req))
                except Exception:
                    continue
        items.sort(key=lambda x: x[0])
        bands = []; start = 0
        for idx, req in items:
            bands.append((f"KULIAH-S{idx}", start, req))
            start += req
        return bands
    except Exception:
        return []

def _compute(total: int, ladder) -> Tuple[str,int,int,float]:
    bands = _bands(ladder)
    if not bands:
        return ("KULIAH-S1", 0, 19000, 0.0)
    cur_band = bands[0]
    for label, start, req in bands:
        if total >= start:
            cur_band = (label, start, req)
        else:
            break
    label, start, req = cur_band
    cur = max(0, total - start)
    if cur > req: cur = req
    pct = 0.0 if req <= 0 else (cur / req) * 100.0
    if pct > 100.0: pct = 100.0
    return label, cur, req, float(f"{pct:.1f}")

class LeinaXPStatusEmbedOverlay(commands.Cog):  # type: ignore[misc]
    def __init__(self, bot: Any):
        self.bot = bot
        self._task: Optional[asyncio.Task] = None
        self._stop = asyncio.Event()

    async def cog_load(self):
        if not ENABLE:
            log.info("[leina:xp_status] disabled"); return
        self._task = self.bot.loop.create_task(self._runner(), name="leina_xp_status")
        log.info("[leina:xp_status] started; targets=%s", _targets())

    async def cog_unload(self):
        if self._task and not self._task.done():
            self._stop.set()
            self._task.cancel()
            try: await self._task
            except asyncio.CancelledError: pass
            log.info("[leina:xp_status] stopped")

    @commands.command(name="xp_mirror")  # type: ignore[attr-defined]
    @commands.is_owner()                 # type: ignore[attr-defined]
    async def xp_mirror(self, ctx: Any, sub: str="sync"):
        ok = await self._sync_once()
        await ctx.reply(f"[xp_mirror] sync -> {'OK' if ok else 'FAIL'}")

    async def _runner(self):
        await asyncio.sleep(5)
        while not self._stop.is_set():
            try:
                await self._sync_once()
            except Exception:
                log.exception("[leina:xp_status] tick error")
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=INTERVAL)
            except asyncio.TimeoutError:
                pass

    async def _sync_once(self) -> bool:
        snap = await self._load_snapshot()
        if not snap:
            log.info("[leina:xp_status] snapshot not ready; skip")
            return False
        ok = await self._write_snapshot_pins(snap)
        return ok

    async def _load_snapshot(self) -> Optional[Dict[str,str]]:
        # 1) Try from pinned JSON (first target)
        if discord is not None:
            try:
                t = _targets()
                if t:
                    ch_id, msg_id = t[0]
                    ch = await self._resolve_channel(ch_id)
                    if ch:
                        msg = await ch.fetch_message(msg_id)
                        snap = self._parse_from_message(msg.content or "")
                        if snap:
                            return snap
            except Exception:
                pass
        # 2) Upstash learning:status_json and senior_total
        if UPSTASH_URL and UPSTASH_TOKEN:
            s = await self._load_from_upstash()
            if s: return s
        # 3) Local seed + ladder
        ladder = _load_ladder()
        total = await self._seed_total()
        if total and total > 0:
            label, cur, req, pct = _compute(total, ladder)
            snap = {
                "xp:stage:label": label,
                "xp:stage:current": str(cur),
                "xp:stage:required": str(req),
                "xp:stage:percent": f"{pct:.1f}",
                "xp:bot:senior_total": str(total),
                "learning:status": f"{label} ({pct:.1f}%)",
                "learning:status_json": json.dumps({
                    "label": label, "percent": pct, "senior_total": total,
                    "stage": {"start_total": total - cur, "required": req, "current": cur},
                    "remaining": max(0, req - cur),
                }, ensure_ascii=False)
            }
            return snap
        return None

    async def _seed_total(self) -> Optional[int]:
        if XP_SEED_ENV:
            return _q_i(XP_SEED_ENV, 0)
        try:
            with open(XP_SEED_FILE, "r", encoding="utf-8") as f:
                js = json.load(f); return _q_i(js.get("senior_total"), 0)
        except Exception:
            return None

    async def _load_from_upstash(self) -> Optional[Dict[str,str]]:
        try:
            import aiohttp
        except Exception:
            return None
        try:
            from urllib.parse import quote
            headers={"Authorization": f"Bearer {UPSTASH_TOKEN}"}
            async with aiohttp.ClientSession(headers=headers) as sess:
                url = f"{UPSTASH_URL.rstrip('/')}/get/{quote('learning:status_json', safe='')}"
                async with sess.get(url, timeout=5) as r:
                    if r.status!=200: return None
                    data = await r.json(content_type=None)
                    js = data.get("result")
                    if not js: return None
                    try:
                        snap_js = json.loads(js)
                    except Exception:
                        return None
                # Optional: senior_total (for line summary)
                try:
                    url2 = f"{UPSTASH_URL.rstrip('/')}/get/{quote('xp:bot:senior_total', safe='')}"
                    async with sess.get(url2, timeout=5) as r2:
                        total_js = await r2.json(content_type=None)
                        total = total_js.get("result")
                except Exception:
                    total = None
            label = snap_js.get("label") or "KULIAH-S1"
            pct = snap_js.get("percent") or 0.0
            stg = snap_js.get("stage") or {}
            cur = _q_i(stg.get("current"), 0)
            req = _q_i(stg.get("required"), 0)
            total = _q_i(total, snap_js.get("senior_total") or 0)
            pct = float(f"{float(pct):.1f}")
            snap = {
                "xp:stage:label": label,
                "xp:stage:current": str(cur),
                "xp:stage:required": str(req),
                "xp:stage:percent": f"{pct:.1f}",
                "xp:bot:senior_total": str(total),
                "learning:status": f"{label} ({pct:.1f}%)",
                "learning:status_json": json.dumps(snap_js, ensure_ascii=False),
            }
            return snap
        except Exception as e:
            log.warning("[leina:xp_status] upstash read failed: %r", e)
            return None

    def _parse_from_message(self, content: str) -> Optional[Dict[str,str]]:
        try:
            m = re.search(r"```json\\s*(?P<body>{.*?})\\s*```", content, re.S)
            if m:
                js = json.loads(m.group("body"))
                label = js.get("label") or "KULIAH-S1"
                pct = float(f"{float(js.get('percent') or 0.0):.1f}")
                stg = js.get("stage") or {}
                cur = _q_i(stg.get("current"), 0)
                req = _q_i(stg.get("required"), 0)
                total = _q_i(js.get("senior_total"), 0)
                return {
                    "xp:stage:label": label,
                    "xp:stage:current": str(cur),
                    "xp:stage:required": str(req),
                    "xp:stage:percent": f"{pct:.1f}",
                    "xp:bot:senior_total": str(total),
                    "learning:status": f"{label} ({pct:.1f}%)",
                    "learning:status_json": json.dumps(js, ensure_ascii=False),
                }
            # fallback line parse
            m2 = re.search(r"xp:stage:label:\\s*(.+)", content); lbl = m2.group(1).strip() if m2 else None
            m3 = re.search(r"xp:stage:current:\\s*(\\d+)", content); cur = int(m3.group(1)) if m3 else None
            m4 = re.search(r"xp:stage:required:\\s*(\\d+)", content); req = int(m4.group(1)) if m4 else None
            m5 = re.search(r"xp:stage:percent:\\s*([0-9]+(?:\\.[0-9]+)?)", content); pct = float(m5.group(1)) if m5 else None
            m6 = re.search(r"xp:bot:senior_total:\\s*(\\d+)", content); tot = int(m6.group(1)) if m6 else None
            if all(v is not None for v in (lbl, cur, req, pct, tot)):
                return {
                    "xp:stage:label": lbl,
                    "xp:stage:current": str(cur),
                    "xp:stage:required": str(req),
                    "xp:stage:percent": f"{pct:.1f}",
                    "xp:bot:senior_total": str(tot),
                    "learning:status": f"{lbl} ({pct:.1f}%)",
                    "learning:status_json": json.dumps({
                        "label": lbl, "percent": pct, "senior_total": tot,
                        "stage": {"start_total": tot - int(cur), "required": int(req), "current": int(cur)},
                        "remaining": max(0, int(req) - int(cur)),
                    }, ensure_ascii=False)
                }
        except Exception:
            pass
        return None

    async def _write_snapshot_pins(self, snap: Dict[str,str]) -> bool:
        ts = _targets()
        if not ts or discord is None:
            return False
        ok_any = False
        for ch_id, msg_id in ts:
            try:
                ch = await self._resolve_channel(ch_id)
                if not ch: 
                    log.warning("[leina:xp_status] channel not found: %s", ch_id); 
                    continue
                try:
                    msg = await ch.fetch_message(msg_id)
                except Exception:
                    if STRICT_EDIT_ONLY:
                        log.warning("[leina:xp_status] msg missing & STRICT_EDIT_ONLY=1 (ch=%s msg=%s)", ch_id, msg_id)
                        continue
                    msg = await ch.send(self._compose_content(snap)); await msg.pin(reason="leina:xp_status bootstrap")
                    ok_any = True; continue
                new_content = self._compose_content(snap)
                if (msg.content or "") != new_content:
                    await msg.edit(content=new_content)
                ok_any = True
            except Exception as e:
                log.warning("[leina:xp_status] write failed ch=%s msg=%s -> %r", ch_id, msg_id, e)
        return ok_any

    def _compose_content(self, snap: Dict[str,str]) -> str:
        try:
            js = json.loads(snap.get("learning:status_json") or "{}")
            js_str = json.dumps(js, ensure_ascii=False, separators=(",", ":"))
        except Exception:
            js_str = "{}"
        label   = snap.get("xp:stage:label","")
        current = snap.get("xp:stage:current","")
        req     = snap.get("xp:stage:required","")
        percent = snap.get("xp:stage:percent","")
        total   = snap.get("xp:bot:senior_total","")
        hdr = snap.get("learning:status") or f"{label} ({percent}%)"
        sep = "-" * 27
        lines = [
            f"**{hdr}**",
            sep,
            f"Stage      : {label}",
            f"Per‑Level  : {current} / {req} XP",
            f"Total      : {total} XP",
            f"Progress   : {percent}%",
            sep,
            "Keys",
            f"xp:stage:label   : {label}",
            f"xp:stage:current : {current}",
            f"xp:stage:required: {req}",
            f"xp:stage:percent : {percent}",
            f"xp:bot:senior_total: {total}",
            sep,
            "```json",
            js_str,
            "```",
            "_auto-updated; jangan diedit manual_",
        ]
        return "\n".join(lines)

    async def _resolve_channel(self, ch_id: int) -> Any:
        if discord is None:
            return None
        ch = self.bot.get_channel(ch_id)
        if getattr(discord, "TextChannel", None) and isinstance(ch, discord.TextChannel):
            return ch
        try:
            ch = await self.bot.fetch_channel(ch_id)
            if getattr(discord, "TextChannel", None) and isinstance(ch, discord.TextChannel):
                return ch
        except Exception:
            pass
        return None

# Loader-agnostic setup
async def setup(bot: Any):
    if _IMPORT_ERR is not None:
        raise _IMPORT_ERR
    await bot.add_cog(LeinaXPStatusEmbedOverlay(bot))  # type: ignore[attr-defined]
    log.info("[leina:xp_status] async setup completed")

def setup(bot: Any):
    if _IMPORT_ERR is not None:
        raise _IMPORT_ERR
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(bot.add_cog(LeinaXPStatusEmbedOverlay(bot)))  # type: ignore[attr-defined]
            log.info("[leina:xp_status] scheduled setup on running loop")
            return
    except Exception:
        pass
    bot.add_cog(LeinaXPStatusEmbedOverlay(bot))  # type: ignore[attr-defined]
    log.info("[leina:xp_status] sync setup completed")
