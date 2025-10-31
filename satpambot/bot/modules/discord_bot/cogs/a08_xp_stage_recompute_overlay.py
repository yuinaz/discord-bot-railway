from __future__ import annotations
import asyncio, json, logging, os, re
from typing import Any, Dict, Optional, Tuple, List
try:
    import discord
    from discord.ext import commands
except Exception as _e:  # Delay hard failure until setup is called
    discord = None  # type: ignore
    commands = None  # type: ignore
    _IMPORT_ERR = _e
else:
    _IMPORT_ERR = None

log = logging.getLogger(__name__)

ENABLE = os.getenv("XP_RECOMPUTE_ENABLE", "1") == "1"
ON_EVENT = os.getenv("XP_RECOMPUTE_ON_EVENT", "1") == "1"
INTERVAL_SEC = int(os.getenv("XP_RECOMPUTE_INTERVAL_SEC", "1800"))
LADDER_FILE = os.getenv("LADDER_FILE", "data/neuro-lite/ladder.json")
XP_TOTAL_KEY = os.getenv("XP_TOTAL_KEY", "xp:bot:senior_total")

UPSTASH_URL = os.getenv("UPSTASH_REDIS_REST_URL", "").strip()
UPSTASH_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN", "").strip()

PIN_CH_ID = int(os.getenv("XP_PIN_CHANNEL_ID", "0") or 0)
PIN_MSG_ID = int(os.getenv("XP_PIN_MESSAGE_ID", "0") or 0)
STRICT_EDIT_ONLY = os.getenv("XP_MIRROR_STRICT_EDIT", "1") == "1"
PIN_TARGETS_STR = os.getenv("XP_PIN_TARGETS", "").strip()

XP_SEED_ENV = os.getenv("XP_SENIOR_TOTAL_SEED") or os.getenv("XP_TOTAL_SEED") or ""
XP_SEED_FILE = os.getenv("XP_SEED_FILE", "data/cache/xp_local_seed.json")

def _q(v, default=0):
    try:
        return int(v)
    except Exception:
        try:
            return int(float(v))
        except Exception:
            return default

def _parse_targets() -> List[Tuple[int,int]]:
    targets: List[Tuple[int,int]] = []
    if PIN_CH_ID and PIN_MSG_ID:
        targets.append((int(PIN_CH_ID), int(PIN_MSG_ID)))
    if PIN_TARGETS_STR:
        for part in re.split(r"[;,\\s]+", PIN_TARGETS_STR):
            if not part: continue
            if ":" in part:
                ch, ms = part.split(":", 1)
                ch = re.sub(r"[^0-9]", "", ch)
                ms = re.sub(r"[^0-9]", "", ms)
                if ch and ms:
                    try: targets.append((int(ch), int(ms)))
                    except Exception: pass
    # dedupe
    seen=set(); uniq=[]
    for t in targets:
        if t not in seen:
            uniq.append(t); seen.add(t)
    return uniq

class XPStageRecomputeOverlay(commands.Cog):  # type: ignore[misc]
    def __init__(self, bot: Any):
        self.bot = bot
        self._task: Optional[asyncio.Task] = None
        self._stop = asyncio.Event()
        self._ladder = None
        self._last_total: Optional[int] = None
        self._targets: List[Tuple[int,int]] = _parse_targets()

    async def cog_load(self):
        if not ENABLE:
            log.info("[xp-recompute] disabled at import (ENABLE=0)")
        self._ladder = self._load_ladder()
        # seeds
        env_seed = _q(XP_SEED_ENV, 0) if XP_SEED_ENV else 0
        if env_seed > 0:
            self._last_total = env_seed
            log.info("[xp-recompute] seeded from ENV -> %s", env_seed)
        file_seed = self._load_seed_file()
        if (file_seed or 0) > (self._last_total or 0):
            self._last_total = file_seed
            log.info("[xp-recompute] seeded from file -> %s", file_seed)
        try:
            pinned_seed = await self._load_seed_from_pinned()
            if (pinned_seed or 0) > (self._last_total or 0):
                self._last_total = pinned_seed
                log.info("[xp-recompute] seeded from pinned -> %s", pinned_seed)
        except Exception as e:
            log.warning("[xp-recompute] read pinned seed failed: %r", e)
        log.info("[xp-recompute] targets=%s | interval=%ss | on_event=%s", self._targets or "[]", INTERVAL_SEC, ON_EVENT)

    @commands.Cog.listener()  # type: ignore[attr-defined]
    async def on_ready(self):
        if not ENABLE:
            return
        if self._task is None or self._task.done():
            self._stop.clear()
            loop = getattr(self.bot, "loop", asyncio.get_event_loop())
            self._task = loop.create_task(self._runner(), name="xp_stage_recompute")
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

    @commands.command(name="xp_seed")  # type: ignore[attr-defined]
    @commands.is_owner()               # type: ignore[attr-defined]
    async def xp_seed(self, ctx: Any, total: int):
        total = _q(total, 0)
        if total <= 0:
            await ctx.reply("seed must be positive int")
            return
        self._last_total = total
        self._save_seed_file(total)
        await ctx.reply(f"[xp] seeded -> {total}")
        await self._recompute()

    @commands.Cog.listener()  # type: ignore[attr-defined]
    async def on_xp_add(self, *args: Any, **kwargs: Any):
        if not (ENABLE and ON_EVENT):
            return
        uid = kwargs.get("uid") or kwargs.get("user_id")
        amt = kwargs.get("amt") or kwargs.get("amount")
        if uid is None or amt is None:
            ints = [a for a in args if isinstance(a, int)]
            if len(ints) >= 2:
                uid, amt = ints[0], ints[1]
        if uid is None or amt is None:
            return
        await asyncio.sleep(0.1)
        await self._recompute(delta=_q(amt, 0))

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
            return {
                "senior": {
                    "KULIAH": {
                        "S1": 19000, "S2": 35000, "S3": 58000, "S4": 70000, "S5": 96500,
                        "S6": 158000, "S7": 220000, "S8": 262500
                    }
                }
            }

    def _bands(self) -> List[Tuple[str,int,int]]:
        try:
            kv = self._ladder["senior"]["KULIAH"]
            items = []
            for k, v in kv.items():
                if isinstance(k, str) and k.upper().startswith("S"):
                    try:
                        idx = int(k[1:])
                        req = _q(v, None)
                        if req is not None:
                            items.append((idx, req))
                    except Exception:
                        continue
            items.sort(key=lambda x: x[0])
            bands = []
            start = 0
            for idx, req in items:
                bands.append((f"KULIAH-S{idx}", start, req))
                start += req
            return bands
        except Exception:
            return []

    def _compute_stage(self, total: int) -> Tuple[str,int,int,float]:
        bands = self._bands()
        if not bands:
            return ("KULIAH-S1", 0, 19000, 0.0)
        current = bands[0]
        for label, start, req in bands:
            if total >= start:
                current = (label, start, req)
            else:
                break
        label, start, req = current
        cur = max(0, total - start)
        if cur > req:
            cur = req
        percent = 0.0 if req <= 0 else (cur / req) * 100.0
        if percent > 100.0:
            percent = 100.0
        return (label, cur, req, percent)

    async def _recompute(self, delta: int = 0):
        total_ok, senior_total = await self._get_senior_total()
        if not total_ok:
            if self._last_total is None:
                seed = self._load_seed_file()
                if seed:
                    self._last_total = seed
                    log.info("[xp-recompute] reloaded seed from file -> %s", seed)
                else:
                    try:
                        seed = await self._load_seed_from_pinned()
                        if seed:
                            self._last_total = seed
                            log.info("[xp-recompute] reloaded seed from pinned -> %s", seed)
                    except Exception:
                        pass
            if self._last_total is None:
                log.warning("[xp-recompute] total unavailable and no seed; skip")
                return
            senior_total = self._last_total + (delta or 0)
        else:
            senior_total = _q(senior_total, self._last_total or 0) + (delta or 0)

        self._last_total = senior_total
        self._save_seed_file(senior_total)

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

        await self._write_snapshot_upstash(snap)
        await self._write_snapshot_pins(snap)
        log.info("[xp-recompute] %s -> %s%% (cur=%s req=%s total=%s)", stage_label, f"{percent:.1f}", current, required, senior_total)

    def _load_seed_file(self) -> Optional[int]:
        try:
            with open(XP_SEED_FILE, "r", encoding="utf-8") as f:
                js = json.load(f)
            v = _q(js.get("senior_total"), 0)
            return v if v > 0 else None
        except Exception:
            return None

    def _save_seed_file(self, total: int):
        try:
            os.makedirs(os.path.dirname(XP_SEED_FILE), exist_ok=True)
            with open(XP_SEED_FILE, "w", encoding="utf-8") as f:
                json.dump({"senior_total": int(total)}, f)
        except Exception as e:
            log.warning("[xp-recompute] save seed failed: %r", e)

    async def _load_seed_from_pinned(self) -> Optional[int]:
        targets = _parse_targets()
        if not targets or discord is None:
            return None
        ch_id, msg_id = targets[0]
        try:
            ch = await self._resolve_channel(ch_id)
            if not ch:
                return None
            msg = await ch.fetch_message(msg_id)
            content = msg.content or ""
            m = re.search(r"```json\\s*(?P<body>{.*?})\\s*```", content, re.S)
            if m:
                js = json.loads(m.group("body"))
                if "senior_total" in js:
                    return _q(js.get("senior_total"), 0) or None
                stage = js.get("stage") or {}
                cur = _q(stage.get("current"), 0)
                start = _q(stage.get("start_total"), 0)
                if cur > 0 or start > 0:
                    return start + cur
            m2 = re.search(r"xp:bot:senior_total:\\s*(\\d+)", content)
            if m2:
                return int(m2.group(1))
        except Exception:
            return None
        return None

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
                async with sess.get(url, timeout=6) as r:
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
                    async with sess.get(url, timeout=6) as r:
                        if r.status!=200:
                            log.warning("[xp-recompute] upstash set %s -> %s", k, r.status)
                            return False
            return True
        except Exception as e:
            log.warning("[xp-recompute] write snapshot upstash failed: %r", e)
            return False

    async def _write_snapshot_pins(self, snap: Dict[str,str]) -> bool:
        targets = self._targets or []
        if not targets or discord is None:
            return False
        ok_any = False
        for ch_id, msg_id in targets:
            try:
                ch = await self._resolve_channel(ch_id)
                if not ch:
                    log.warning("[xp-recompute] pin channel not found: %s", ch_id); continue
                try:
                    msg = await ch.fetch_message(msg_id)
                except Exception:
                    if STRICT_EDIT_ONLY:
                        log.warning("[xp-recompute] pin message missing & STRICT_EDIT_ONLY=1 (ch=%s msg=%s)", ch_id, msg_id)
                        continue
                    content = self._compose_pin_content(snap)
                    msg = await ch.send(content); await msg.pin(reason="XP snapshot bootstrap")
                    ok_any = True; continue
                new_content = self._compose_pin_content(snap)
                if (msg.content or "") != new_content:
                    await msg.edit(content=new_content)
                ok_any = True
            except Exception as e:
                log.warning("[xp-recompute] write pinned failed ch=%s msg=%s -> %r", ch_id, msg_id, e)
        return ok_any

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

# ---- Loader compatibility (async & sync) ----
async def setup(bot: Any):
    if _IMPORT_ERR is not None:
        raise _IMPORT_ERR
    cog = XPStageRecomputeOverlay(bot)
    await bot.add_cog(cog)  # type: ignore[attr-defined]
    log.info("[xp-recompute] async setup completed")

def setup(bot: Any):
    if _IMPORT_ERR is not None:
        raise _IMPORT_ERR
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Schedule async setup in the running loop
            loop.create_task(bot.add_cog(XPStageRecomputeOverlay(bot)))  # type: ignore[attr-defined]
            log.info("[xp-recompute] scheduled setup on running loop")
            return
    except Exception:
        pass
    # Fallback: add_cog synchronously if possible (discord.py v1 style)
    bot.add_cog(XPStageRecomputeOverlay(bot))  # type: ignore[attr-defined]
    log.info("[xp-recompute] sync setup completed")
