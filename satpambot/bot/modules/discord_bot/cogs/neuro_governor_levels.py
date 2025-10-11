
from __future__ import annotations
import json, time, logging, os
from pathlib import Path
from typing import Any, Dict

import discord
from discord.ext import commands, tasks

log = logging.getLogger(__name__)

BASE = Path("data/neuro-lite")
BASE.mkdir(parents=True, exist_ok=True)

LP_J = BASE / "learn_progress_junior.json"
LP_S = BASE / "learn_progress_senior.json"
BRIDGE_OVERRIDE = BASE / "bridge_override.json"    # {"split":{"junior":0,"senior":1},"ts":...}
GATE_STATUS = BASE / "gate_status.json"            # {"phase":"junior|senior_*|done", ...}
PUBLIC_GATE = BASE / "public_gate.json"            # {"locked":true, "requests":[...]}

OWNERS = set(int(x) for x in os.getenv("NEURO_GOVERNOR_OWNERS","").split(",") if x.strip().isdigit())

def _load_json(p: Path, default: Dict[str, Any]) -> Dict[str, Any]:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return json.loads(json.dumps(default))

def _save_json(p: Path, d: Dict[str, Any]):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")

def _block_done(block: Dict[str, int]) -> bool:
    # block is like {"L1": 100, "L2": 50, ...}
    if not isinstance(block, dict) or not block:
        return False
    return all(int(v) >= 100 for v in block.values())

def _avg(block: Dict[str, int]) -> int:
    try:
        vals = [int(v) for v in block.values()]
        return int(round(sum(vals)/max(1,len(vals))))
    except Exception:
        return 0

class NeuroGovernorLevels(commands.Cog):
    """
    Sub-phase senior:
      junior -> senior_smp -> senior_sma -> senior_kuliah -> done

    - Auto shift XP route to senior when junior 100% (write bridge_override.json).
    - Keeps public gate locked until owner approves.
    - Prefix commands: !governor_status, !go_public_request, !go_public_approve, !go_public_lock
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._loop.start()

    def cog_unload(self):
        self._loop.cancel()

    @tasks.loop(seconds=60)
    async def _loop(self):
        gs = _load_json(GATE_STATUS, {"phase":"junior", "promotion_allowed": False, "ts": int(time.time())})
        pg = _load_json(PUBLIC_GATE, {"locked": True, "requests": []})
        lpj = _load_json(LP_J, {"overall": 0})
        lps = _load_json(LP_S, {"overall": 0})

        junior_ok = int(lpj.get("overall", 0)) >= 100

        # Detect senior block structure (SMP/SMA/KULIAH) or fallback (SD)
        smp = lps.get("SMP", {})
        sma = lps.get("SMA", {})
        kul = lps.get("KULIAH", {})
        has_subblocks = bool(smp or sma or kul)

        # 1) Promote to senior stream when junior completed
        if junior_ok and gs.get("phase") == "junior":
            _save_json(BRIDGE_OVERRIDE, {"split": {"junior": 0, "senior": 1}, "ts": int(time.time())})
            gs["phase"] = "senior_smp" if has_subblocks else "senior"
            gs["promotion_allowed"] = True
            gs["ts"] = int(time.time())
            log.info("[governor] auto-promote: XP dialihkan ke senior (phase=%s)", gs["phase"])

        # 2) Handle senior sub-phases
        if has_subblocks:
            if gs.get("phase") in ("senior_smp","senior_sma","senior_kuliah"):
                smp_done = _block_done(smp)
                sma_done = _block_done(sma)
                kul_done = _block_done(kul)

                if gs["phase"] == "senior_smp" and smp_done:
                    gs["phase"] = "senior_sma"
                    gs["ts"] = int(time.time())
                    log.info("[governor] phase -> senior_sma (SMP complete)")
                if gs["phase"] == "senior_sma" and sma_done:
                    gs["phase"] = "senior_kuliah"
                    gs["ts"] = int(time.time())
                    log.info("[governor] phase -> senior_kuliah (SMA complete)")
                if gs["phase"] == "senior_kuliah" and kul_done:
                    gs["phase"] = "done"
                    gs["ts"] = int(time.time())
                    log.info("[governor] phase -> done (Kuliah complete)")
        else:
            # Fallback: single senior phase based on overall
            if gs.get("phase") == "senior" and int(lps.get("overall", 0)) >= 100:
                gs["phase"] = "done"
                gs["ts"] = int(time.time())
                log.info("[governor] phase -> done (Senior overall 100%)")

        # Persist
        gs.setdefault("block_progress", {})
        if has_subblocks:
            gs["block_progress"] = {
                "SMP": _avg(smp) if smp else 0,
                "SMA": _avg(sma) if sma else 0,
                "KULIAH": _avg(kul) if kul else 0
            }
        _save_json(GATE_STATUS, gs)
        _save_json(PUBLIC_GATE, pg)

    @_loop.before_loop
    async def _wait_ready(self):
        await self.bot.wait_until_ready()

    # ------- Commands (prefix) -------
    @commands.command(name="governor_status")
    async def governor_status(self, ctx: commands.Context):
        gs = _load_json(GATE_STATUS, {"phase":"junior", "promotion_allowed": False})
        pg = _load_json(PUBLIC_GATE, {"locked": True, "requests": []})
        bp = gs.get("block_progress", {})
        desc = (f"**Governor Status**\n"
                f"- Phase: `{gs.get('phase')}`\n"
                f"- Promotion allowed: `{gs.get('promotion_allowed')}`\n"
                f"- Public gate locked: `{pg.get('locked')}`")
        if bp:
            desc += (f"\n- Progress SMP/SMA/Kuliah: "
                     f"`{bp.get('SMP',0)}% / {bp.get('SMA',0)}% / {bp.get('KULIAH',0)}%`")
        try:
            await ctx.reply(desc, mention_author=False)
        except Exception:
            await ctx.send(desc)

    @commands.command(name="go_public_request")
    async def go_public_request(self, ctx: commands.Context):
        pg = _load_json(PUBLIC_GATE, {"locked": True, "requests": []})
        req = {"user_id": ctx.author.id, "name": getattr(ctx.author, "display_name", str(ctx.author)), "ts": int(time.time())}
        pg.setdefault("requests", []).append(req)
        _save_json(PUBLIC_GATE, pg)
        await ctx.reply("✅ Permintaan go-public terkirim. Menunggu persetujuan owner.", mention_author=False)

    @commands.command(name="go_public_approve")
    async def go_public_approve(self, ctx: commands.Context):
        if OWNERS and ctx.author.id not in OWNERS:
            return await ctx.reply("❌ Kamu bukan owner yang terdaftar.", mention_author=False)
        pg = _load_json(PUBLIC_GATE, {"locked": True, "requests": []})
        if not pg.get("requests"):
            return await ctx.reply("Tidak ada request tertunda.", mention_author=False)
        pg["locked"] = False
        pg["approved_by"] = ctx.author.id
        pg["approved_ts"] = int(time.time())
        _save_json(PUBLIC_GATE, pg)
        await ctx.reply("🟢 Public gate dibuka. Bot boleh go-public (per aturan cogs lain).", mention_author=False)

    @commands.command(name="go_public_lock")
    async def go_public_lock(self, ctx: commands.Context):
        if OWNERS and ctx.author.id not in OWNERS:
            return await ctx.reply("❌ Kamu bukan owner yang terdaftar.", mention_author=False)
        pg = _load_json(PUBLIC_GATE, {"locked": True, "requests": []})
        pg["locked"] = True
        _save_json(PUBLIC_GATE, pg)
        await ctx.reply("🔴 Public gate dikunci kembali.", mention_author=False)

async def setup(bot: commands.Bot):
    await bot.add_cog(NeuroGovernorLevels(bot))
