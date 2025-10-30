
from __future__ import annotations
import os, json, logging, asyncio
from discord.ext import commands

log = logging.getLogger(__name__)

def _envb(k, d=True):
    v = os.getenv(k)
    if v is None: return d
    return str(v).strip().lower() in {"1","true","on","yes"}

def _int(v, d=0):
    try: return int(v)
    except Exception:
        try: return int(float(v))
        except Exception: return d

class LearningStatusRepairOnce(commands.Cog):
    """One-shot repair: ensure learning:status follows KULIAH/MAGANG pinned stage,
    and migrate any SMP/SMA miner state to xp:miner:* keys.
    Enabled when REPAIR_LEARNING_STATUS_ONCE=1 (default)."""
    def __init__(self, bot):
        self.bot = bot
        self.enabled = _envb("REPAIR_LEARNING_STATUS_ONCE", True)
        self.total_key = os.getenv("XP_SENIOR_KEY","xp:bot:senior_total")
        self.k_miner_label   = os.getenv("XP_MINER_LABEL_KEY","xp:miner:label")
        self.k_miner_current = os.getenv("XP_MINER_CURRENT_KEY","xp:miner:current")
        self.k_miner_req     = os.getenv("XP_MINER_REQUIRED_KEY","xp:miner:required")
        self.k_miner_pct     = os.getenv("XP_MINER_PERCENT_KEY","xp:miner:percent")
        self._done = False

    async def _run_once(self):
        if self._done or not self.enabled:
            return
        try:
            from satpambot.bot.modules.discord_bot.helpers.discord_pinned_kv import PinnedJSONKV
            kv = PinnedJSONKV(self.bot)
            m = await kv.get_map()  # pinned KV snapshot (plus some mirrored keys)

            # Read main stage (pinned)
            stage_label   = str(m.get("xp:stage:label") or "")
            stage_current = _int(m.get("xp:stage:current", 0), 0)
            stage_req     = _int(m.get("xp:stage:required", 1), 1)
            stage_pct     = float(m.get("xp:stage:percent", 0) or 0.0)
            total         = _int(m.get(self.total_key, 0), 0)

            # Read learning:status_json (may contain wrong SMP-* state)
            raw = m.get("learning:status_json")
            try: lj = json.loads(raw) if isinstance(raw, str) else (raw or {})
            except Exception: lj = {}

            learning_label = str(lj.get("label") or "")
            # If learning label is non-KULIAH and main stage is KULIAH/MAGANG, repair it.
            if stage_label.startswith(("KULIAH-","MAGANG")) and not learning_label.startswith(("KULIAH-","MAGANG")):
                status = f"{stage_label} ({stage_pct}%)"
                status_json = json.dumps({
                    "label": stage_label, "percent": stage_pct, "remaining": max(0, stage_req - stage_current),
                    "senior_total": total, "stage": {"start_total": max(0, total - stage_current), "required": stage_req, "current": stage_current}
                }, separators=(",",":"))
                await kv.set_multi({
                    "learning:status": status,
                    "learning:status_json": status_json,
                })
                log.warning("[repair-once] fixed learning:status -> %s %s/%s (%.1f%%)", stage_label, stage_current, stage_req, stage_pct)

                # Migrate old learning SMP-* to xp:miner:* if present
                if learning_label and not learning_label.startswith(("KULIAH-","MAGANG")):
                    cur = _int(((lj.get("stage") or {}).get("current", 0)), 0)
                    req = _int(((lj.get("stage") or {}).get("required", 0)), 0)
                    pct = float(lj.get("percent", 0) or 0.0)
                    await kv.set_multi({
                        self.k_miner_label: learning_label,
                        self.k_miner_current: cur,
                        self.k_miner_req: req,
                        self.k_miner_pct: pct,
                    })
                    log.warning("[repair-once] migrated learning miner -> %s %s/%s (%.1f%%)", learning_label, cur, req, pct)

            self._done = True
        except Exception as e:
            log.debug("[repair-once] skip: %r", e)

    @commands.Cog.listener()
    async def on_ready(self):
        await self.bot.wait_until_ready()
        asyncio.create_task(self._run_once())

async def setup(bot: commands.Bot):
    await bot.add_cog(LearningStatusRepairOnce(bot))
