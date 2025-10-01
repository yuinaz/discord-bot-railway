# -*- coding: utf-8 -*-
"""
First-touch Attachment Ban — v11.1.1 (NO ENV)
- Selective auto-delete: default HANYA di threads "fp" & "whitelist".
- Tidak auto-delete di "Ban Log" & parent log channel.
- Tetap: exact-match ke thread `imagephising` → ban via Safety; pHash rendah → auto-whitelist tanpa spam.

Jika config lama (v11.1) dipakai, nilai default HARD di bawah akan aktif.
"""
from __future__ import annotations

import json
import os
import hashlib
from typing import Optional, Set, Dict, Any

import discord
from discord.ext import commands

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
    "direct_ban_on_strong": False,

    # Reference
    "reference_required_for_ban": True,
    "reference_thread_name": "imagephising",
    "reference_cache_minutes": 15,

    # Channel/thread binding
    "log_channel_name": "log-botphising",
    "fp_log_thread_name": "imagephising-fp-log",
    "ban_log_thread_name": "Ban Log",
    "whitelist_thread_name": "whitelist",
    "log_channel_id": 0,

    # Whitelist
    "whitelist_file": "config/image_whitelist_sha256.json",
    "skip_logging_if_whitelisted": True,

    # Auto-whitelist
    "auto_whitelist_enabled": True,
    "auto_whitelist_if_phash_below": 0.85,
    "auto_whitelist_log_to_thread": True,

    # Auto-delete (selective)
    "auto_delete_logs_enabled": True,
    "auto_delete_logs_seconds": 600,
    "auto_delete_fp_thread": True,
    "auto_delete_whitelist_thread": True,
    "auto_delete_ban_thread": False,
    "auto_delete_parent_log_channel": False,
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

        # reference
        self.reference_required_for_ban = bool(_cfg_get(cfg, "reference_required_for_ban"))
        self.reference_thread_name = str(_cfg_get(cfg, "reference_thread_name"))
        self.reference_cache_minutes = int(_cfg_get(cfg, "reference_cache_minutes"))

        # bindings
        lcid = int(_cfg_get(cfg, "log_channel_id") or 0)
        self._log_channel_id = lcid if lcid > 0 else None
        self.log_channel_name = str(_cfg_get(cfg, "log_channel_name") or "").strip()
        self.fp_log_thread_name = str(_cfg_get(cfg, "fp_log_thread_name") or "").strip()
        self.ban_log_thread_name = str(_cfg_get(cfg, "ban_log_thread_name") or "").strip()
        self.whitelist_thread_name = str(_cfg_get(cfg, "whitelist_thread_name") or "").strip()

        # whitelist
        self.whitelist_file = str(_cfg_get(cfg, "whitelist_file"))
        self.skip_logging_if_whitelisted = bool(_cfg_get(cfg, "skip_logging_if_whitelisted"))

        # auto-whitelist
        self.auto_whitelist_enabled = bool(_cfg_get(cfg, "auto_whitelist_enabled"))
        self.auto_whitelist_if_phash_below = float(_cfg_get(cfg, "auto_whitelist_if_phash_below"))
        self.auto_whitelist_log_to_thread = bool(_cfg_get(cfg, "auto_whitelist_log_to_thread"))

        # auto-delete logs
        self.auto_delete_logs_enabled = bool(_cfg_get(cfg, "auto_delete_logs_enabled"))
        self.auto_delete_logs_seconds = int(_cfg_get(cfg, "auto_delete_logs_seconds"))
        self.auto_delete_fp_thread = bool(_cfg_get(cfg, "auto_delete_fp_thread"))
        self.auto_delete_whitelist_thread = bool(_cfg_get(cfg, "auto_delete_whitelist_thread"))
        self.auto_delete_ban_thread = bool(_cfg_get(cfg, "auto_delete_ban_thread"))
        self.auto_delete_parent_log_channel = bool(_cfg_get(cfg, "auto_delete_parent_log_channel"))

        # internals
        self._ref_cache: Dict[int, Dict[str, Any]] = {}   # guild_id -> {"hashes": set(str), "ts": datetime}
        self._wl_cache: Set[str] = set()

        self._load_whitelist()

    # ------------- whitelist file -------------
    def _load_whitelist(self):
        try:
            with open(self.whitelist_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    self._wl_cache = {str(x) for x in data}
                elif isinstance(data, dict) and "sha256" in data:
                    self._wl_cache = {str(x) for x in data.get("sha256", [])}
        except Exception:
            self._wl_cache = set()

    def _save_whitelist(self):
        try:
            os.makedirs(os.path.dirname(self.whitelist_file), exist_ok=True)
            with open(self.whitelist_file, "w", encoding="utf-8") as f:
                json.dump(sorted(list(self._wl_cache)), f, indent=2)
        except Exception:
            pass

    # ------------- helpers -------------
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

    def _delete_after_for(self, tag: str) -> Optional[float]:
        """tag: 'fp' | 'whitelist' | 'ban' | 'parent'"""
        if not self.auto_delete_logs_enabled:
            return None
        flags = {
            "fp": self.auto_delete_fp_thread,
            "whitelist": self.auto_delete_whitelist_thread,
            "ban": self.auto_delete_ban_thread,
            "parent": self.auto_delete_parent_log_channel,
        }
        return float(self.auto_delete_logs_seconds) if flags.get(tag, False) else None

    async def _send_log(self, guild: discord.Guild, embed: discord.Embed, *, thread: Optional[discord.Thread]=None, delete_after: Optional[float]=None):
        ch = self._resolve_log_channel(guild)
        if not ch:
            return None
        try:
            if thread:
                return await thread.send(embed=embed, delete_after=delete_after) if delete_after else await thread.send(embed=embed)
            else:
                return await ch.send(embed=embed, delete_after=delete_after) if delete_after else await ch.send(embed=embed)
        except Exception:
            return None

    # ------------- reference index -------------
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
        from datetime import datetime, timezone
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

    # ------------- pHash -------------
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
        return {"best_conf": best, "details": details}

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

    # ------------- safety pipeline -------------
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

    # ------------- main -------------
    async def _act(self, member: discord.Member, message: discord.Message):
        guild = member.guild
        parent = self._resolve_log_channel(guild)
        fp_thread = self._find_thread(guild, parent, self.fp_log_thread_name)
        ban_thread = self._find_thread(guild, parent, self.ban_log_thread_name)
        wl_thread = self._find_thread(guild, parent, self.whitelist_thread_name)

        ref = await self._get_reference_index(guild)
        ref_count = ref["count"]; ref_hashes = ref["hashes"]

        # sha list
        sha_list = []
        exact_hit = False
        for att in message.attachments:
            h = await self._sha256_of_attachment(att)
            if h:
                sha_list.append(h)
                if h in ref_hashes:
                    exact_hit = True

        # skip if already whitelisted
        whitelisted = any(h in self._wl_cache for h in sha_list)
        if whitelisted and self.skip_logging_if_whitelisted:
            return

        # exact → ban
        if exact_hit or not self.reference_required_for_ban:
            base = discord.Embed(
                title="First-touch detected",
                description=(f"User: {member.mention} (`{member.id}`)\n"
                             f"Channel: {message.channel.mention}\n"
                             f"RefThread='{self.reference_thread_name}' entries={ref_count} | exact_hit={exact_hit}\n"
                             f"SafetyRequired={self.safety_required} | RefRequiredForBan={self.reference_required_for_ban}"),
                color=0x3498DB, timestamp=_utcnow(),
            )
            base.set_footer(text="SatpamBot • FirstTouchAttachmentBan v11.1.1")
            base.url = getattr(message, "jump_url", discord.Embed.Empty)
            await self._send_log(guild, base, thread=ban_thread, delete_after=self._delete_after_for("ban"))

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
                "labels": ["first_touch","attachment","reference_exact" if exact_hit else "no_reference","no_env_cog","v11.1.1"],
            }
            submitted = await self._submit_via_pipeline(member, message, "First-touch attachment policy", meta)
            if submitted:
                ack = discord.Embed(title="Sent to Safety", description="Autoban request (exact match) masuk pipeline.", color=0x2980B9, timestamp=_utcnow())
                await self._send_log(guild, ack, thread=ban_thread, delete_after=self._delete_after_for("ban"))
                return
            if not self.safety_required:
                e = discord.Embed(title="Direct BAN (no safety)", description="Pipeline tidak ada dan safety_required=False.", color=0xE74C3C, timestamp=_utcnow())
                await self._send_log(guild, e, thread=ban_thread, delete_after=self._delete_after_for("ban"))
                await self._ban_member_direct(member)
                return
            warn = discord.Embed(title="SKIPPED (no safety)", description="Safety pipeline tidak ada.", color=0xF1C40F, timestamp=_utcnow())
            await self._send_log(guild, warn, thread=fp_thread, delete_after=self._delete_after_for("fp"))
            return

        # not exact → evaluate pHash
        ph = await self._phash_quick_check(message)
        best = float(ph.get("best_conf") or 0.0)

        # AUTO-WHITELIST
        if self.auto_whitelist_enabled and best < self.auto_whitelist_if_phash_below:
            added = 0
            for h in sha_list:
                if h not in self._wl_cache:
                    self._wl_cache.add(h); added += 1
            if added:
                self._save_whitelist()

            if self.auto_whitelist_log_to_thread:
                emb = discord.Embed(
                    title="Auto-whitelist (non-phish)",
                    description=(f"pHash best_conf={best:.3f} < {self.auto_whitelist_if_phash_below:.2f}\n"
                                 f"Origin: {getattr(message,'jump_url','n/a')}"),
                    color=0x2ECC71, timestamp=_utcnow(),
                )
                await self._send_log(guild, emb, thread=wl_thread, delete_after=self._delete_after_for("whitelist"))
            return

        # otherwise → FP review (no ban)
        base = discord.Embed(
            title="First-touch detected",
            description=(f"User: {member.mention} (`{member.id}`)\n"
                         f"Channel: {message.channel.mention}\n"
                         f"RefThread='{self.reference_thread_name}' entries={ref_count} | exact_hit=False\n"
                         f"SafetyRequired={self.safety_required} | RefRequiredForBan={self.reference_required_for_ban}"),
            color=0x3498DB, timestamp=_utcnow(),
        )
        base.set_footer(text="SatpamBot • FirstTouchAttachmentBan v11.1.1")
        base.url = getattr(message, "jump_url", discord.Embed.Empty)
        await self._send_log(guild, base, thread=fp_thread, delete_after=self._delete_after_for("fp"))

        note = discord.Embed(
            title="Skip ban: no exact match in reference thread",
            description=(f"pHash best_conf={best:.3f}. Review manual jika diperlukan."),
            color=0xF1C40F, timestamp=_utcnow(),
        )
        await self._send_log(guild, note, thread=fp_thread, delete_after=self._delete_after_for("fp"))

async def setup(bot: commands.Bot):
    if bot.get_cog("FirstTouchAttachmentBan") is None:
        await bot.add_cog(FirstTouchAttachmentBan(bot))
