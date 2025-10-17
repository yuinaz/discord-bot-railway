
# -*- coding: utf-8 -*-
"""
Overlay cog: XP_STATE reads from Upstash (source of truth) instead of local shadow XP.

Drop this file into:
  satpambot/bot/modules/discord_bot/cogs/a08_xp_state_from_upstash_overlay.py

Safe for smoke import: no side effects on import. Only activates when setup(bot) is called by discord.py.
"""
import os
import time
import json
from typing import Any, Dict, List, Optional

import asyncio

try:
    import httpx
except Exception:
    httpx = None  # Will raise on use with a clear message

from discord.ext import commands

def _env(name: str, default: Optional[str] = None) -> Optional[str]:
    v = os.environ.get(name, default)
    if v is None or str(v).strip() == "":
        return default
    return v

class _UpstashClient:
    def __init__(self) -> None:
        self.base = (_env("UPSTASH_REDIS_REST_URL") or "").rstrip("/")
        self.token = _env("UPSTASH_REDIS_REST_TOKEN") or ""
        if not self.base or not self.token:
            raise RuntimeError("UPSTASH_REDIS_REST_URL / UPSTASH_REDIS_REST_TOKEN not set")
        if httpx is None:
            raise RuntimeError("httpx is not installed. pip install httpx")

    async def pipeline(self, commands: List[List[str]]) -> List[Optional[str]]:
        headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=10.0) as cli:
            r = await cli.post(f"{self.base}/pipeline", headers=headers, json={"commands": commands})
            r.raise_for_status()
            data = r.json()
        # Upstash returns {"result": [...]} or {"results": [...]} depending on region; normalize:
        result = data.get("result") or data.get("results") or []
        # each item may be {"result": "123"} or raw "123"
        out = []
        for item in result:
            if isinstance(item, dict):
                out.append(item.get("result"))
            else:
                out.append(item)
        return out

def _normalize_phase(raw: Optional[str]) -> str:
    if not raw:
        return "tk"
    s = str(raw).strip().lower()
    # normalize common variants
    aliases = {
        "tk-l1": "tk",
        "tk_l1": "tk",
        "kindergarten": "tk",
        "junior": "sd",
        "elementary": "sd",
        "smp": "smp",
        "sma": "sma",
        "university": "kuliah",
        "college": "kuliah",
        "senior": "senior",
    }
    return aliases.get(s, s)

def _level_from_phase_and_total(phase: str, total: int) -> str:
    # TK/Ladder defaults; you can override with env:
    # thresholds expressed as CSV for simplicity: "TK-L1:0;TK-L2:500;TK-L3:1000"
    ladder_env = _env("XP_TK_LADDER", "TK-L1:0;TK-L2:500;TK-L3:1000")
    ladder = []
    for part in ladder_env.split(";"):
        if not part.strip():
            continue
        name, val = part.split(":")
        ladder.append((name.strip(), int(val.strip())))
    ladder.sort(key=lambda x: x[1])
    if phase == "senior":
        return "SENIOR"
    if phase in ("sd", "smp", "sma", "kuliah"):
        return phase.upper()
    # TK ladder
    curr = ladder[0][0]
    for name, th in ladder:
        if total >= th:
            curr = name
    return curr

async def fetch_upstash_xp(uid: int) -> Dict[str, Any]:
    """
    Returns {"total": int, "level": str, "phase": str, "updated": int}
    Pulls from keys:
      HGET xp:user:{uid} total
      HGET xp:user:{uid} level (fallback computed)
      GET learning:phase
      GET xp:bot:senior_total (optional for sanity)
    """
    cli = _UpstashClient()
    user_key = f"xp:user:{uid}"
    cmds = [
        ["HGET", user_key, "total"],
        ["HGET", user_key, "level"],
        ["GET", "learning:phase"],
        ["GET", "xp:bot:senior_total"],
        ["GET", "xp:bot:tk_total"],
    ]
    res = await cli.pipeline(cmds)
    total_s = res[0] or "0"
    level_s = res[1]
    phase_s = res[2]
    # convert opportunistically
    try:
        total = int(str(total_s))
    except Exception:
        total = 0
    phase = _normalize_phase(phase_s)
    level = level_s or _level_from_phase_and_total(phase, total)
    return {"total": total, "level": level, "phase": phase, "updated": int(time.time())}

class XPStateUpstashBridge(commands.Cog):
    """Expose /xp_state_fix which always reads from Upstash (source of truth)."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="xp_state_fix", description="Show XP_STATE pulled directly from Upstash.")
    async def xp_state_fix(self, ctx: commands.Context):
        try:
            uid = ctx.author.id
            data = await fetch_upstash_xp(uid)
            pretty = json.dumps(data, ensure_ascii=False)
            await ctx.reply(f"[XP_STATE]\n```json\n{pretty}\n```")
        except Exception as e:
            await ctx.reply(f"xp_state_fix error: {e!r}")

    @commands.Cog.listener()
    async def on_ready(self):
        # Log once
        print("[a08_xp_state_from_upstash_overlay] ready — XP_STATE will be fetched via Upstash on /xp_state_fix")

async def get_xp_state_from_upstash(uid: int) -> Dict[str, Any]:
    return await fetch_upstash_xp(uid)

async def setup(bot):
    await bot.add_cog(XPStateUpstashBridge(bot))
