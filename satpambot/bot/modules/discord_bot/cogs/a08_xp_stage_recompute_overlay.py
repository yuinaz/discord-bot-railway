from __future__ import annotations
import asyncio, json, logging, os, re, time, urllib.parse
from typing import Any, Dict, Optional, Tuple, List
import discord
from discord.ext import commands

log = logging.getLogger(__name__)

# ===== ENV =====
ENABLE = os.getenv("XP_RECOMPUTE_ENABLE", "1") == "1"
ON_EVENT = os.getenv("XP_RECOMPUTE_ON_EVENT", "1") == "1"
INTERVAL_SEC = int(os.getenv("XP_RECOMPUTE_INTERVAL_SEC", "1800"))  # default 30m
LADDER_FILE = os.getenv("LADDER_FILE", "data/neuro-lite/ladder.json")
XP_TOTAL_KEY = os.getenv("XP_TOTAL_KEY", "xp:bot:senior_total")

# Upstash
UPSTASH_URL = os.getenv("UPSTASH_REDIS_REST_URL", "").strip()
UPSTASH_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN", "").strip()

# Pinned message (edit-only)
PIN_CH_ID = int(os.getenv("XP_PIN_CHANNEL_ID", "0") or 0)
PIN_MSG_ID = int(os.getenv("XP_PIN_MESSAGE_ID", "0") or 0)
STRICT_EDIT_ONLY = os.getenv("XP_MIRROR_STRICT_EDIT", "1") == "1"

JSON_BLOCK_RE = re.compile(r"```json\s*(?P<body>\{.*?\})\s*```", re.S)

def _q(v, default=0):
    try:
        return int(v)
    except Exception:
        try:
            return int(float(v))
        except Exception:
            return default

class XPStageRecomputeOverlay(commands.Cog):
    """
    Recompute XP stage snapshot (label/current/required/percent) based on senior_total and ladder.json.
    - Runs on periodic interval and (optionally) on each XP event.
    - Writes snapshot keys to Upstash and also edits pinned JSON (no spam).
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._task: Optional[asyncio.Task] = None
        self._stop = asyncio.Event()
        self._ladder = None
        self._last_total: Optional[int] = None

    async def cog_load(self):
        if not ENABLE:
            log.info("[xp-recompute] disabled")
            return
        self._ladder = self._load_ladder()
        log.info("[xp-recompute] ladder loaded")

    @commands.Cog.listener()
    async def on_ready(self):
        if not ENABLE:
            return
        if self._task is None or self._task.done():
            self._stop.clear()
            self._task = self.bot.loop.create_task(self._runner(), name="xp_stage_recompute")
            log.info("[xp-recompute] scheduler started (%ss)", INTERVAL_SEC)

    async def cog_unload(self):
        if self._task and not self._task.done():
            self._stop.set()
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            log.info("[xp-recompute] scheduler stopped")

    # Accept any signature of on_xp_add; normalize to (uid, amt, reason)
    @commands.Cog.listener()
    async def on_xp_add(self, *args: Any, **kwargs: Any):
        if not (ENABLE and ON_EVENT):
            return
        uid = kwargs.get("uid") or kwargs.get("user_id")
        amt = kwargs.get("amt") or kwargs.get("amount")
        if uid is None or amt is None:
            # try positional (uid:int, amt:int, reason:str, ...)
            ints = [a for a in args if isinstance(a, int)]
            if len(ints) >= 2:
                uid, amt = ints[0], ints[1]
        if uid is None or amt is None:
            return
        # small debounce to allow INCR to settle
        await asyncio.sleep(0.1)
        await self._recompute(delta=_q(amt, 0))

    # ===== Core =====
    async def _runner(self):
        await asyncio.sleep(5)
        while not self._stop.is_set():
            try:
                await self._recompute()
            except Exception:
                log.exception("[xp-recompute] tick error")
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=INTERVAL_SEC)
            except asyncio.TimeoutError:
                pass

    def _load_ladder(self):
        try:
            with open(LADDER_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log.warning("[xp-recompute] ladder load failed: %r", e)
            # minimal default
            return {
                "senior": {
                    "KULIAH": {
                        "S1": 19000, "S2": 35000, "S3": 58000, "S4": 70000, "S5": 96500,
                        "S6": 158000, "S7": 220000, "S8": 262500
                    }
                }
            }

    def _bands(self) -> List[Tuple[str,int]]:
        # returns list like [("KULIAH-S1", 19000), ...] sorted by threshold
        try:
            ks = self._ladder["senior"]["KULIAH"]
            items = [(f"KULIAH-{k}", int(v)) for k,v in ks.items()]
            items.sort(key=lambda x: x[1])
            return items
        except Exception:
            return []

    async def _recompute(self, delta: int = 0):
        total_ok, senior_total = await self._get_senior_total()
        if not total_ok:
            # if fail, but we have last_total and delta, use optimistic local
            if self._last_total is None:
                log.warning("[xp-recompute] total unavailable")
                return
            senior_total = self._last_total + delta
        else:
            senior_total = _q(senior_total, self._last_total or 0)
            if delta:
                senior_total += delta  # Upstash GET may be slightly behind; include delta heuristically
        self._last_total = senior_total

        stage_label, current, required, percent = self._compute_stage(senior_total)
        snap = {
            "xp:stage:label": stage_label,
            "xp:stage:current": str(current),
            "xp:stage:required": str(required),
            "xp:stage:percent": f"{percent:.1f}",
            "xp:bot:senior_total": str(senior_total),
            "learning:status": f"{stage_label} ({percent:.1f}%)",
            "learning:status_json": json.dumps({
                "label": stage_label,
                "percent": float(f"{percent:.1f}"),
                "remaining": max(0, required - current),
                "senior_total": senior_total,
                "stage": {
                    "start_total": senior_total - current,
                    "required": required,
                    "current": current
                }
            }, ensure_ascii=False)
        }

        # write to Upstash
        await self._write_snapshot_upstash(snap)
        # update pinned
        await self._write_snapshot_pinned(snap)
        log.info("[xp-recompute] %s -> %s%% (cur=%s req=%s total=%s)", stage_label, f"{percent:.1f}", current, required, senior_total)

    def _compute_stage(self, total: int) -> Tuple[str,int,int,float]:
        bands = self._bands()
        if not bands:
            return ("KULIAH-S1", 0, 19000, 0.0)
        # find current stage: last threshold <= total
        current_stage = bands[0]
        for label, thresh in bands:
            if total >= thresh:
                current_stage = (label, thresh)
            else:
                break
        # next threshold (or same if last)
        idx = [i for i,(l,th) in enumerate(bands) if (l,th)==current_stage][0]
        next_thresh = bands[idx+1][1] if idx+1 < len(bands) else current_stage[1]
        required = max(1, next_thresh - current_stage[1])
        current = max(0, total - current_stage[1])
        percent = (current/required)*100 if required>0 else 100.0
        return (current_stage[0], current, required, percent)

    async def _get_senior_total(self) -> Tuple[bool, Optional[int]]:
        if not (UPSTASH_URL and UPSTASH_TOKEN):
            return False, None
        try:
            import aiohttp
        except Exception as e:
            log.warning("[xp-recompute] aiohttp missing: %r", e)
            return False, None
        try:
            headers={"Authorization": f"Bearer {UPSTASH_TOKEN}"}
            from urllib.parse import quote
            url=f"{UPSTASH_URL.rstrip('/')}/get/{quote(XP_TOTAL_KEY, safe='')}"
            async with aiohttp.ClientSession(headers=headers) as sess:
                async with sess.get(url, timeout=8) as r:
                    if r.status!=200:
                        return False, None
                    data = await r.json(content_type=None)
                    val = (data or {}).get("result")
                    if val is None:
                        return False, None
                    return True, int(val)
        except Exception as e:
            log.warning("[xp-recompute] get total failed: %r", e)
            return False, None

    async def _write_snapshot_upstash(self, snap: Dict[str,str]) -> bool:
        if not (UPSTASH_URL and UPSTASH_TOKEN):
            return False
        try:
            import aiohttp
        except Exception as e:
            log.warning("[xp-recompute] aiohttp missing: %r", e)
            return False
        try:
            headers={"Authorization": f"Bearer {UPSTASH_TOKEN}"}
            from urllib.parse import quote
            async with aiohttp.ClientSession(headers=headers) as sess:
                for k,v in snap.items():
                    url=f"{UPSTASH_URL.rstrip('/')}/set/{quote(k,safe='')}/{quote(v,safe='')}"
                    async with sess.get(url, timeout=8) as r:
                        if r.status!=200:
                            log.warning("[xp-recompute] upstash set %s -> %s", k, r.status)
                            return False
            return True
        except Exception as e:
            log.warning("[xp-recompute] write snapshot upstash failed: %r", e)
            return False

    async def _write_snapshot_pinned(self, snap: Dict[str,str]) -> bool:
        if not (PIN_CH_ID and PIN_MSG_ID):
            return False
        try:
            ch = await self._resolve_channel(PIN_CH_ID)
            if not ch:
                log.warning("[xp-recompute] pin channel not found: %s", PIN_CH_ID); return False
            msg = await ch.fetch_message(PIN_MSG_ID)
        except discord.NotFound:
            if STRICT_EDIT_ONLY:
                log.warning("[xp-recompute] pin message missing & STRICT_EDIT_ONLY=1"); return False
            try:
                ch = await self._resolve_channel(PIN_CH_ID)
                if not ch: return False
                content = self._compose_pin_content(snap)
                msg = await ch.send(content); await msg.pin(reason="XP snapshot bootstrap"); return True
            except Exception as e:
                log.warning("[xp-recompute] create pinned failed: %r", e); return False
        except Exception as e:
            log.warning("[xp-recompute] fetch pinned failed: %r", e); return False

        try:
            new_content = self._compose_pin_content(snap)
            if (msg.content or "") == new_content:
                return True
            await msg.edit(content=new_content)
            return True
        except Exception as e:
            log.warning("[xp-recompute] edit pinned failed: %r", e); return False

    def _compose_pin_content(self, snap: Dict[str,str]) -> str:
        try:
            js = json.loads(snap.get("learning:status_json") or "{}")
            js_str = json.dumps(js, ensure_ascii=False, separators=(",", ":"))
        except Exception:
            js_str = "{}"
        header = "**{}**".format(snap.get("learning:status") or "XP Snapshot")
        lines = [header, "", "```json", js_str, "```", ""]
        for k in ["xp:stage:label","xp:stage:current","xp:stage:required","xp:stage:percent","xp:bot:senior_total"]:
            v = (snap.get(k) or "").strip()
            if v:
                lines.append(f"{k}: {v}")
        return "\n".join(lines)

    async def _resolve_channel(self, ch_id: int) -> Optional[discord.TextChannel]:
        ch = self.bot.get_channel(ch_id)
        if isinstance(ch, discord.TextChannel): return ch
        try:
            ch = await self.bot.fetch_channel(ch_id)
            if isinstance(ch, discord.TextChannel): return ch
        except Exception:
            pass
        return None

async def setup(bot: commands.Bot):
    if not ENABLE:
        log.info("[xp-recompute] loaded but disabled")
    await bot.add_cog(XPStageRecomputeOverlay(bot))
