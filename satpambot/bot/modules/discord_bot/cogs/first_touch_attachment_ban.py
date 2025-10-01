
# -*- coding: utf-8 -*-
"""
First-touch Attachment Ban — v9 (NO ENV)
Focus: **reference thread "imagephising" exact-match** to avoid false positives.
Still pHash + Safety aware, with thread bindings.

Flow:
1) First attachment from a user → check **exact SHA256 match** against attachments in the
   reference thread (default name: "imagephising" under "log-botphising").
   - If exact match found → forward ban request to Safety (AutobanSafetyInterceptor/BanQueueWatcher).
   - If not found → proceed to pHash quick check:
       • strong (>= threshold) → forward to Safety (label "phash_strong")
       • suspected → forward to Safety (label "phash_suspected")
       • no signal → only log to FP thread (review), no ban request.
2) If Safety pipeline not present and safety_required=True ⇒ SKIP (anti FP).

No ENV. Names & thresholds can be changed in optional JSON config.
"""
from __future__ import annotations

import json
import os
import hashlib
from typing import Optional, Set, Dict, Any

import discord
from discord.ext import commands

# ------------------- HARD DEFAULTS -------------------
HARD = {
    "enabled": True,
    "always": True,
    "window_min": 60,
    "only_roleless": False,
    "exempt_staff": True,
    "exempt_role_names": [],
    "exempt_role_ids": [],
    "whitelist_channels": [],
    "delete_message_days": 7,

    # Safety & pHash
    "safety_required": True,
    "phash_min_threshold": 0.90,
    "phash_strong_threshold": 0.98,
    "direct_ban_on_strong": False,     # only used when safety_required=False

    # Reference thread strategy
    "reference_required_for_ban": True,   # require exact match in reference thread for ban request
    "reference_thread_name": "imagephising",
    "reference_cache_minutes": 15,

    # Channel/thread binding
    "log_channel_name": "log-botphising",
    "fp_log_thread_name": "imagephising-fp-log",
    "ban_log_thread_name": "Ban Log",
    "whitelist_thread_name": "whitelist",
    "log_channel_id": 0,
}

CFG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "..", "..",
    "config", "first_touch_attachment_ban.json"
)

def _load_cfg() -> Dict[str, Any]:
    try:
        with open(CFG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
    except Exception:
        pass
    return {}

def _cfg_get(cfg: Dict[str, Any], key: str):
    return cfg.get(key, HARD[key])

def _utcnow():
    import datetime
    return datetime.datetime.now(datetime.timezone.utc)

async def _maybe_await(res):
    if hasattr(res, "__await__"):
        return await res
    return res

class FirstTouchAttachmentBan(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        cfg = _load_cfg()

        # behavior
        self.enabled = bool(_cfg_get(cfg, "enabled"))
        self.always = bool(_cfg_get(cfg, "always"))
        self.window_min = int(_cfg_get(cfg, "window_min"))
        self.only_roleless = bool(_cfg_get(cfg, "only_roleless"))
        self.exempt_staff = bool(_cfg_get(cfg, "exempt_staff"))
        self.exempt_role_names = {str(x).lower() for x in _cfg_get(cfg, "exempt_role_names") or []}
        self.exempt_role_ids = {int(x) for x in _cfg_get(cfg, "exempt_role_ids") or []}
        self.whitelist_channels = {str(x).lower() for x in _cfg_get(cfg, "whitelist_channels") or []}
        self.delete_message_days = int(_cfg_get(cfg, "delete_message_days"))

        # safety & phash
        self.safety_required = bool(_cfg_get(cfg, "safety_required"))
        self.phash_min_threshold = float(_cfg_get(cfg, "phash_min_threshold"))
        self.phash_strong_threshold = float(_cfg_get(cfg, "phash_strong_threshold"))
        self.direct_ban_on_strong = bool(_cfg_get(cfg, "direct_ban_on_strong"))

        # reference & bindings
        self.reference_required_for_ban = bool(_cfg_get(cfg, "reference_required_for_ban"))
        self.reference_thread_name = str(_cfg_get(cfg, "reference_thread_name"))
        self.reference_cache_minutes = int(_cfg_get(cfg, "reference_cache_minutes"))

        lcid = int(_cfg_get(cfg, "log_channel_id") or 0)
        self._log_channel_id = lcid if lcid > 0 else None
        self.log_channel_name = str(_cfg_get(cfg, "log_channel_name") or "").strip()
        self.fp_log_thread_name = str(_cfg_get(cfg, "fp_log_thread_name") or "").strip()
        self.ban_log_thread_name = str(_cfg_get(cfg, "ban_log_thread_name") or "").strip()
        self.whitelist_thread_name = str(_cfg_get(cfg, "whitelist_thread_name") or "").strip()

        # internals
        self._banning: Set[int] = set()
        self._seen_once: Set[int] = set()
        self._ref_cache: Dict[int, Dict[str, Any]] = {}  # guild_id -> {"hashes": set(str), "ts": datetime}

    # ------------------- helpers -------------------
    def _is_staff(self, member: discord.Member) -> bool:
        p = member.guild_permissions
        return p.administrator or p.manage_guild or p.ban_members

    def _is_roleless(self, member: discord.Member) -> bool:
        return sum(1 for r in getattr(member, "roles", []) if not getattr(r, "is_default", False)) == 0

    def _is_exempt_by_role(self, member: discord.Member) -> bool:
        names = {getattr(r, "name", "").lower() for r in getattr(member, "roles", [])}
        if self.exempt_role_names & names:
            return True
        ids = {getattr(r, "id", 0) for r in getattr(member, "roles", [])}
        if self.exempt_role_ids & ids:
            return True
        return False

    def _within_window(self, member: discord.Member) -> bool:
        if self.always:
            return True
        if not member.joined_at:
            return False
        return (_utcnow() - member.joined_at).total_seconds() <= max(0, self.window_min) * 60

    # ---------- Channel / Thread resolution ----------
    def _resolve_log_channel(self, guild: discord.Guild) -> Optional[discord.TextChannel]:
        if self._log_channel_id:
            ch = guild.get_channel(self._log_channel_id)
            if isinstance(ch, discord.TextChannel):
                return ch
        if self.log_channel_name:
            ch = discord.utils.get(guild.text_channels, name=self.log_channel_name)
            if isinstance(ch, discord.TextChannel):
                return ch
        for name in ("log-botphising","log-satpam","log-satpam-bot","logs","moderation-log"):
            ch = discord.utils.get(guild.text_channels, name=name)
            if isinstance(ch, discord.TextChannel):
                return ch
        return None

    def _find_thread(self, guild: discord.Guild, parent: Optional[discord.TextChannel], thread_name: str) -> Optional[discord.Thread]:
        if not thread_name:
            return None
        if parent:
            for th in parent.threads:
                if th.name.lower() == thread_name.lower():
                    return th
        try:
            for th in guild.threads:
                if th.name.lower() == thread_name.lower() and (parent is None or th.parent_id == parent.id):
                    return th
        except Exception:
            pass
        return None

    async def _send_log(self, guild: discord.Guild, embed: discord.Embed, *, thread: Optional[discord.Thread]=None):
        ch = self._resolve_log_channel(guild)
        if not ch:
            return
        try:
            if thread:
                await thread.send(embed=embed)
            else:
                await ch.send(embed=embed)
        except Exception:
            pass

    # ------------------- Reference index (exact SHA256) -------------------
    async def _build_reference_index(self, guild: discord.Guild) -> Dict[str, Any]:
        parent = self._resolve_log_channel(guild)
        ref_thread = self._find_thread(guild, parent, self.reference_thread_name)
        hashes = set()
        if not ref_thread:
            return {"hashes": hashes, "count": 0}

        try:
            async for msg in ref_thread.history(limit=None, oldest_first=True):
                for att in getattr(msg, "attachments", []):
                    try:
                        b = await att.read()
                        h = hashlib.sha256(b).hexdigest()
                        hashes.add(h)
                    except Exception:
                        continue
        except Exception:
            pass
        return {"hashes": hashes, "count": len(hashes)}

    async def _get_reference_index(self, guild: discord.Guild) -> Dict[str, Any]:
        from datetime import datetime, timedelta, timezone
        now = datetime.now(timezone.utc)
        entry = self._ref_cache.get(guild.id)
        if entry and (now - entry["ts"]).total_seconds() <= self.reference_cache_minutes * 60:
            return entry
        ref = await self._build_reference_index(guild)
        self._ref_cache[guild.id] = {"hashes": ref["hashes"], "count": ref["count"], "ts": now}
        return self._ref_cache[guild.id]

    async def _sha256_of_attachment(self, att: discord.Attachment) -> Optional[str]:
        try:
            b = await att.read()
            return hashlib.sha256(b).hexdigest()
        except Exception:
            return None

    # ------------------- pHASH QUICK CHECK -------------------
    async def _phash_quick_check(self, message: discord.Message) -> Dict[str, Any]:
        details = []; best = 0.0
        cog_names = ("AntiImagePhashRuntime", "PhashAutoBan", "AntiImagePhishAdvanced", "AntiImagePhishGuard")
        meth_names = ("check_attachment", "is_phish_attachment", "phash_check", "classify_attachment", "score_attachment")

        for a in message.attachments:
            info = {"filename": a.filename, "content_type": getattr(a, "content_type", None), "size": getattr(a, "size", None)}
            score_for_this = None
            for cn in cog_names:
                cog = self.bot.get_cog(cn)
                if not cog:
                    continue
                for mn in meth_names:
                    fn = getattr(cog, mn, None)
                    if not callable(fn):
                        continue
                    try:
                        res = fn(attachment=a, message=message, author=message.author, channel=message.channel)
                        res = await _maybe_await(res)
                    except TypeError:
                        try:
                            res = fn(a, message); res = await _maybe_await(res)
                        except Exception:
                            continue
                    except Exception:
                        continue
                    conf = self._interpret_phash_result(res)
                    if conf is not None:
                        score_for_this = conf if (score_for_this is None or conf > score_for_this) else score_for_this
                        break
                if score_for_this is not None:
                    break
            if score_for_this is None:
                details.append({"attachment": info, "confidence": None, "source": None})
            else:
                best = max(best, float(score_for_this))
                details.append({"attachment": info, "confidence": float(score_for_this), "source": "cog"})
        strong = best >= self.phash_strong_threshold
        return {"best_conf": best, "details": details, "strong": strong}

    def _interpret_phash_result(self, res: Any) -> Optional[float]:
        try:
            if isinstance(res, dict):
                if "confidence" in res: return max(0.0, min(1.0, float(res["confidence"])))
                if "score" in res: return max(0.0, min(1.0, float(res["score"])))
                if "ratio" in res: return max(0.0, min(1.0, float(res["ratio"])))
                if "distance" in res: return max(0.0, min(1.0, 1.0 - float(res["distance"])/64.0))
            if isinstance(res, (list, tuple)) and len(res)>=1 and isinstance(res[0], (int,float)):
                return max(0.0, min(1.0, float(res[0])))
            if isinstance(res, (int,float)): return max(0.0, min(1.0, float(res)))
            if isinstance(res, bool): return 1.0 if res else 0.0
        except Exception:
            return None
        return None

    # ------------------- SAFETY PIPELINE -------------------
    async def _submit_via_pipeline(self, member: discord.Member, message: discord.Message, reason: str, meta: Dict[str, Any]) -> bool:
        for cog_name in ("AutobanSafetyInterceptor", "BanQueueWatcher"):
            cog = self.bot.get_cog(cog_name)
            if not cog:
                continue
            for meth_name in ("request_ban", "enqueue_ban", "enqueue", "queue_ban", "submit"):
                meth = getattr(cog, meth_name, None)
                if callable(meth):
                    try:
                        res = meth(member=member, reason=reason, delete_message_days=self.delete_message_days, metadata=meta)
                        await _maybe_await(res)
                        return True
                    except TypeError:
                        try:
                            res = meth(member, reason, self.delete_message_days, meta)
                            await _maybe_await(res)
                            return True
                        except Exception:
                            continue
                    except Exception:
                        continue
        try:
            self.bot.dispatch("satpam_autoban_request", member.guild, member, reason, self.delete_message_days, meta)
            return True
        except Exception:
            return False

    async def _ban_member_direct(self, member: discord.Member):
        try:
            try:
                await member.guild.ban(member, reason="First-touch attachment policy",
                                       delete_message_seconds=min(7*24*3600, self.delete_message_days*24*3600))
            except TypeError:
                await member.guild.ban(member, reason="First-touch attachment policy",
                                       delete_message_days=min(7, self.delete_message_days))
        except Exception:
            raise

    # ------------------- MAIN ACTION -------------------
    async def _act(self, member: discord.Member, message: discord.Message):
        guild = member.guild
        parent = self._resolve_log_channel(guild)
        fp_thread = self._find_thread(guild, parent, self.fp_log_thread_name)
        ban_thread = self._find_thread(guild, parent, self.ban_log_thread_name)
        ref_thread = self._find_thread(guild, parent, self.reference_thread_name)

        # Reference index
        ref = await self._get_reference_index(guild)
        ref_count = ref["count"]; ref_hashes = ref["hashes"]

        # Compute SHA256 for incoming attachments
        exact_hit = False; sha_list = []
        for att in message.attachments:
            h = await self._sha256_of_attachment(att)
            if h:
                sha_list.append(h)
                if h in ref_hashes:
                    exact_hit = True

        # Build base embed
        base = discord.Embed(
            title="First-touch detected",
            description=(f"User: {member.mention} (`{member.id}`)\n"
                         f"Channel: {message.channel.mention}\n"
                         f"RefThread='{self.reference_thread_name}' entries={ref_count} | exact_hit={exact_hit}\n"
                         f"SafetyRequired={self.safety_required} | RefRequiredForBan={self.reference_required_for_ban}"),
            color=0x3498DB, timestamp=_utcnow(),
        )
        base.set_footer(text="SatpamBot • FirstTouchAttachmentBan v9")
        await self._send_log(guild, base, thread=(ban_thread if exact_hit else fp_thread))

        # Decision tree
        if self.reference_required_for_ban and not exact_hit:
            # No exact match → try pHash to assist review; DO NOT request ban
            ph = await self._phash_quick_check(message)
            best = ph["best_conf"]; label = "unknown"
            if best >= self.phash_strong_threshold: label = "phash_strong"
            elif best >= self.phash_min_threshold: label = "phash_suspected"
            note = discord.Embed(
                title="Skip ban: no exact match in reference thread",
                description=f"pHash best_conf={best:.3f} label={label}. Dikirim ke FP thread untuk review.",
                color=0xF1C40F, timestamp=_utcnow(),
            )
            await self._send_log(guild, note, thread=fp_thread)
            return

        # Exact match (or ref not required) → build metadata and submit
        meta = {
            "trigger": "first_touch_attachment",
            "match": "reference_exact" if exact_hit else "no_reference",
            "sha256": sha_list,
            "mode": "ALWAYS" if self.always else "JOIN_WINDOW",
            "delete_message_days": self.delete_message_days,
            "message_id": getattr(message, "id", None),
            "channel_id": getattr(message.channel, "id", None),
            "author_id": getattr(member, "id", None),
            "guild_id": getattr(member.guild, "id", None),
            "attachments": [{
                "filename": a.filename,
                "content_type": a.content_type,
                "size": getattr(a, "size", None),
                "url": getattr(a, "url", None),
                "proxy_url": getattr(a, "proxy_url", None),
            } for a in message.attachments],
            "ts": _utcnow().isoformat(),
            "labels": ["first_touch", "attachment", "reference_exact" if exact_hit else "no_reference", "no_env_cog", "v9"],
        }

        submitted = await self._submit_via_pipeline(member, message, "First-touch attachment policy", meta)
        if submitted:
            ack = discord.Embed(title="Sent to Safety", description=f"Autoban request (match={'exact' if exact_hit else 'none'}) masuk pipeline.", color=0x2980B9, timestamp=_utcnow())
            await self._send_log(guild, ack, thread=(ban_thread if exact_hit else fp_thread))
            return

        # No safety
        if exact_hit and not self.safety_required:
            e = discord.Embed(title="Direct BAN (exact reference match, no safety)",
                              description="Pipeline tidak ada dan safety_required=False.", color=0xE74C3C, timestamp=_utcnow())
            await self._send_log(guild, e, thread=ban_thread)
            await self._ban_member_direct(member)
            return

        warn = discord.Embed(title="SKIPPED (no safety)", description="Safety pipeline tidak ada dan safety_required=True.", color=0xF1C40F, timestamp=_utcnow())
        await self._send_log(guild, warn, thread=fp_thread)

    # ------------------- listener -------------------
    @commands.Cog.listener("on_message")
    async def _on_message(self, message: discord.Message):
        if not self.enabled or not message.guild:
            return
        if message.author.bot or not message.attachments:
            return
        member = message.author if isinstance(message.author, discord.Member) else message.guild.get_member(message.author.id)
        if not isinstance(member, discord.Member):
            return

        # exemptions
        if self.exempt_staff and self._is_staff(member):
            return
        if self._is_exempt_by_role(member):
            return
        if (getattr(message.channel, "name", "") or "").lower() in self.whitelist_channels:
            return
        if member.id in self._seen_once:
            return
        if self.only_roleless and not self._is_roleless(member):
            return
        if not self._within_window(member):
            return

        self._seen_once.add(member.id)
        await self._act(member, message)

async def setup(bot: commands.Bot):
    if bot.get_cog("FirstTouchAttachmentBan") is None:
        await bot.add_cog(FirstTouchAttachmentBan(bot))
