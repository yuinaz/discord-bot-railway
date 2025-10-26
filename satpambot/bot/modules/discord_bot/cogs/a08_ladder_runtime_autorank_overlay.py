# SPDX-License-Identifier: MIT
# a08_ladder_runtime_autorank_overlay.py
#
# Auto-rank with RESET-PER-STAGE semantics using ladder *quotas*.
# Supports phases: KULIAH -> MAGANG -> WORK (overall) -> GOVERNOR (policy gate).
#
# - Reads XP from Upstash REST (XP_SENIOR_KEY).
# - Loads ladder quotas from data files (kuliah quotas; magang quota; work overall quotas).
# - Every LADDER_REFRESH_SECS, recompute current phase+stage and write:
#     learning:status         e.g., "KULIAH-S6 (12.3%)"
#     learning:status_json    { label, percent, remaining, senior_total, stage:{start_total, required, current} }
# - Optional: upsert a single embed message in a channel (no DM) if PROGRESS_CHANNEL_ID/LOG_CHANNEL_ID/QNA_CHANNEL_ID is set.
#
# ENV
#   XP_SENIOR_KEY                default: xp:bot:senior_total
#   UPSTASH_REST_URL|UPSTASH_REDIS_REST_URL
#   UPSTASH_REST_TOKEN|UPSTASH_REDIS_REST_TOKEN
#   LADDER_REFRESH_SECS          default: 60
#   PROGRESS_CHANNEL_ID|LOG_CHANNEL_ID|QNA_CHANNEL_ID (optional embed)
#
from __future__ import annotations
import os, json, asyncio, logging
from typing import Dict, Any, List, Tuple, Optional

import discord
from discord.ext import commands, tasks

log = logging.getLogger(__name__)

def _get_env(*names: str, default: str="") -> str:
    for n in names:
        v = os.getenv(n)
        if v and str(v).strip():
            return str(v).strip()
    return default

def _upstash_base_and_auth() -> Tuple[str, Dict[str, str]]:
    base = _get_env("UPSTASH_REST_URL", "UPSTASH_REDIS_REST_URL").rstrip("/")
    token = _get_env("UPSTASH_REST_TOKEN", "UPSTASH_REDIS_REST_TOKEN")
    if not base or not token:
        return "", {}
    return base, {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

async def _http_json(session, method: str, url: str, *, headers: Dict[str,str], json_body: Any=None) -> Any:
    import aiohttp
    async with session.request(method, url, headers=headers, json=json_body) as resp:
        try:
            data = await resp.json()
        except Exception:
            txt = await resp.text()
            return {"status": resp.status, "text": txt}
        return data

async def _get_xp(session) -> Optional[int]:
    base, headers = _upstash_base_and_auth()
    if not base:
        return None
    key = _get_env("XP_SENIOR_KEY", default="xp:bot:senior_total")
    payload = [["GET", key]]
    data = await _http_json(session, "POST", f"{base}/pipeline", headers=headers, json_body=payload)
    try:
        res = data[0]["result"]
        return int(res) if res is not None else None
    except Exception:
        return None

def _load_json_candidates(cands: List[str]) -> Optional[Dict[str,Any]]:
    for p in cands:
        try:
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            continue
    # try package data
    try:
        import importlib.resources as ir
        with ir.files("satpambot.bot.data").joinpath("ladder.json").open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None

def _load_kuliah_quotas() -> List[int]:
    # quotas per stage (S1..S8), not cumulative
    # we accept either quota-format file or cumulative format and infer quotas
    # prefer explicit quotas from data/neuro-lite/ladder.json
    d = _load_json_candidates([
        "data/neuro-lite/ladder.json",
        "satpambot/bot/data/ladder.json",
        "data_templates/ladder_default.json",
    ]) or {}
    k = d.get("KULIAH") or d.get("kuliah") or {}
    # Accept both quota fields or cumulative fields. If cumulative >= ascending, derive quotas by diffing.
    # If values look like quotas (e.g., around the mentioned numbers), use them directly.
    keys = ["S1","S2","S3","S4","S5","S6","S7","S8"]
    vals = [k.get(x) for x in keys]
    if all(isinstance(v, (int,float)) for v in vals if v is not None) and all(vals):
        # Heuristic: if strictly increasing and S2 > S1 by small margin, likely cumulative; if S5 is 96500, treat as QUOTA.
        increasing = all(vals[i] > vals[i-1] for i in range(1, len(vals)))
        if increasing:
            # decide: treat as quotas as per user requirement (reset per stage with ladder values)
            quotas = [int(v) for v in vals]  # direct quotas
        else:
            quotas = [int(v) for v in vals]
    else:
        # fallback conservative
        quotas = [19000,35000,58000,70000,96500,158000,220000,262500]
    return quotas

def _load_magang_quota() -> int:
    d = _load_json_candidates([
        "data/neuro-lite/ladder.json",
        "satpambot/bot/data/ladder.json",
    ]) or {}
    m = d.get("MAGANG") or d.get("magang") or {}
    # keys may include "1TH"
    v = m.get("1TH") or m.get("S1") or m.get("quota") or 2000000
    return int(v)

def _load_work_overall_quotas() -> List[int]:
    d = _load_json_candidates([
        "data/config/xp_work_ladder.json",
    ]) or {}
    o = d.get("overall") or {}
    Ls = ["L1","L2","L3","L4"]
    vals = [int(o.get(k)) for k in Ls if o.get(k) is not None]
    if not vals:
        vals = [5000000,7000000,9000000,12000000]
    return vals

def _phase_for_total(total: int, kuliah_q: List[int], magang_q: int, work_q: List[int]) -> Tuple[str,int,int,int]:
    """
    Returns (phase_label, stage_index, prev_sum, required)
    - phase_label: 'KULIAH' or 'MAGANG' or 'WORK' or 'GOVERNOR'
    - stage_index: 1-based index within phase (for label), or 1 for MAGANG
    - prev_sum: cumulative sum at start of current stage
    - required: quota required to finish the current stage
    """
    # KULIAH ranges
    cum = 0
    for i, q in enumerate(kuliah_q, start=1):
        nxt = cum + q
        if total < nxt:
            return "KULIAH", i, cum, q
        cum = nxt
    # MAGANG
    mag_start = cum
    if total < mag_start + magang_q:
        return "MAGANG", 1, mag_start, magang_q
    # WORK overall
    cum2 = mag_start + magang_q
    for i, q in enumerate(work_q, start=1):
        nxt = cum2 + q
        if total < nxt:
            return "WORK", i, cum2, q
        cum2 = nxt
    # Beyond all -> GOVERNOR (show last WORK L as 100% and label GOVERNOR)
    return "GOVERNOR", 1, cum2, 1

def _format_label(phase: str, idx: int) -> str:
    if phase == "KULIAH":
        return f"KULIAH-S{idx}"
    if phase == "MAGANG":
        return "MAGANG-S1"
    if phase == "WORK":
        return f"WORK-L{idx}"
    return "GOVERNOR"

async def _write_status(session, label: str, percent: float, remaining: int, xp: int, start_total: int, required: int) -> None:
    base, headers = _upstash_base_and_auth()
    if not base:
        return
    payload = [
        ["SET", "learning:status", f"{label} ({percent:.1f}%)"],
        ["SET", "learning:status_json", json.dumps({
            "label": label,
            "percent": round(percent,1),
            "remaining": remaining,
            "senior_total": xp,
            "stage": {
                "start_total": start_total,
                "required": required,
                "current": xp - start_total
            }
        })],
    ]
    await _http_json(session, "POST", f"{base}/pipeline", headers=headers, json_body=payload)

async def _upsert_embed(bot: discord.Client, label: str, percent: float, remaining: int, xp: int, start_total:int, required:int) -> None:
    try:
        from satpambot.bot.modules.discord_bot.helpers.embed_scribe import EmbedScribe
    except Exception:
        return
    channel_id = _get_env("PROGRESS_CHANNEL_ID", "LOG_CHANNEL_ID", "QNA_CHANNEL_ID")
    if not channel_id:
        return
    title = "Leina Progress"
    desc = f"**{label}** — {percent:.1f}%\nXP: `{xp}` • Stage: `{xp-start_total}/{required}` • Sisa: `{remaining}`"
    try:
        await EmbedScribe.upsert(
            bot,
            channel_id=channel_id,
            title=title,
            description=desc,
            marker="[leina:xp_status]",
            pin=True,
            edit_only=False
        )
    except Exception as e:
        log.info("[autorank] embed upsert skipped: %r", e)

class LadderAutoRank(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._last_label = None
        self._last_json = None
        refresh = int(_get_env("LADDER_REFRESH_SECS", default="60") or "60")
        self._loop.change_interval(seconds=max(10, refresh))
        self._loop.start()

    def cog_unload(self):
        try:
            self._loop.cancel()
        except Exception:
            pass

    @tasks.loop(seconds=60.0)
    async def _loop(self):
        try:
            await self._tick()
        except Exception as e:
            log.warning("[autorank] tick error: %r", e)

    @_loop.before_loop
    async def _wait_ready(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(5.0)

    async def _tick(self):
        import aiohttp
        async with aiohttp.ClientSession() as session:
            xp = await _get_xp(session)
            if xp is None:
                return
            kq = _load_kuliah_quotas()
            mq = _load_magang_quota()
            wq = _load_work_overall_quotas()
            phase, idx, start_total, required = _phase_for_total(xp, kq, mq, wq)
            label = _format_label(phase, idx)
            current = max(0, xp - start_total)
            remaining = max(0, required - current)
            percent = 100.0 if required <= 0 else min(100.0, (current/required)*100.0)

            # Build json fingerprint to avoid unnecessary writes
            j = {
                "label": label,
                "percent": round(percent,1),
                "remaining": remaining,
                "senior_total": xp,
                "stage": {"start_total": start_total, "required": required, "current": current},
            }
            jkey = json.dumps(j, sort_keys=True)
            if jkey != self._last_json:
                await _write_status(session, label, percent, remaining, xp, start_total, required)
                await _upsert_embed(self.bot, label, percent, remaining, xp, start_total, required)
                self._last_json = jkey
                self._last_label = label
                log.warning("[autorank] %s (%.1f%%) xp=%s", label, percent, xp)

async def setup(bot: commands.Bot):
    await bot.add_cog(LadderAutoRank(bot))
