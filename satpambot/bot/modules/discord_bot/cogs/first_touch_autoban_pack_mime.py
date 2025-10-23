# -*- coding: utf-8 -*-
from __future__ import annotations

from discord.ext import commands

import re, json, os, contextlib, logging
from typing import List, Dict, Any, Optional
import discord

log = logging.getLogger(__name__)

HARD = {
    "enabled": True,
    "exempt_threads": True,
    "only_roleless": False,
    "exempt_role_ids": [],
    "exempt_role_names": [],
    "whitelist_channels": [],
    "pattern_pack_min_attachments": 3,
    "pattern_pack_allow_image_prefix": True,
    "pattern_pack_exts": ["jpg", "jpeg", "png", "gif", "webp"],
    "require_consecutive_numbers": True,
    "mime_direct_ban_min_mismatches": 3,
    "image_kinds": ["jpeg", "png", "webp", "gif"],
    "log_channel_id": 0,
    "delete_message_days": 7,
}

CFG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "..", "..",
    "config", "first_touch_autoban_pack_mime.json"
)

def _load_cfg() -> Dict[str, Any]:
    try:
        with open(CFG_PATH, "r", encoding="utf-8") as f:
            d = json.load(f)
            return d if isinstance(d, dict) else {}
    except Exception:
        return {}

def _cfg(cfg, k): return cfg.get(k, HARD.get(k))
def _name_parts(name: str):
    name = (name or "").rsplit("/", 1)[-1].rsplit("\\", 1)[-1].lower()
    if "." in name: stem, ext = name.rsplit(".", 1)
    else: stem, ext = name, ""
    return stem, ext

def _sniff_image_kind(b: bytes) -> str:
    if len(b) >= 4:
        if b[:3] == b"\xFF\xD8\xFF": return "jpeg"
        if b[:8] == b"\x89PNG\r\n\x1a\n": return "png"
        if b[:4] == b"RIFF" and b[8:12] == b"WEBP": return "webp"
        if b[:6] in (b"GIF87a", b"GIF89a"): return "gif"
    return "unknown"

class FirstTouchAutoBanPackMime(commands.Cog):
    """Strict: ban hanya jika PACK berurutan (>=3) **dan** burst MIME mismatch (>=3)."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        cfg = _load_cfg()
        self.enabled = bool(_cfg(cfg, "enabled"))
        self.exempt_threads = bool(_cfg(cfg, "exempt_threads"))
        self.only_roleless = bool(_cfg(cfg, "only_roleless"))
        self.exempt_role_ids = {int(x) for x in (_cfg(cfg, "exempt_role_ids") or [])}
        self.exempt_role_names = {str(x).lower() for x in (_cfg(cfg, "exempt_role_names") or [])}
        self.whitelist_channels = {str(x).lower() for x in (_cfg(cfg, "whitelist_channels") or [])}
        self.pack_min = int(_cfg(cfg, "pattern_pack_min_attachments"))
        self.pack_allow_image_prefix = bool(_cfg(cfg, "pattern_pack_allow_image_prefix"))
        self.pack_exts = {str(x).lower() for x in (_cfg(cfg, "pattern_pack_exts") or [])}
        self.require_consecutive = bool(_cfg(cfg, "require_consecutive_numbers"))
        self.mime_direct_ban_min_mismatches = int(_cfg(cfg, "mime_direct_ban_min_mismatches"))
        self.image_kinds = {str(x).lower() for x in (_cfg(cfg, "image_kinds") or [])}
        self._log_channel_id = int(_cfg(cfg, "log_channel_id") or 0) or None
        self.delete_message_days = int(_cfg(cfg, "delete_message_days"))

    async def _resolve_log(self, guild: discord.Guild) -> Optional[discord.TextChannel]:
        if self._log_channel_id:
            ch = guild.get_channel(self._log_channel_id)
            if isinstance(ch, discord.TextChannel): return ch
        return guild.system_channel

    async def _log_embed(self, guild, title, desc, color, url=None):
        ch = await self._resolve_log(guild)
        if not ch: return
        e = discord.Embed(title=title, description=desc, color=color)
        if url: e.url = url
        with contextlib.suppress(Exception): await ch.send(embed=e)

    async def _ban(self, guild, member_or_user, reason):
        with contextlib.suppress(Exception):
            if isinstance(member_or_user, discord.Member):
                await member_or_user.ban(reason=reason, delete_message_days=self.delete_message_days); return
        with contextlib.suppress(Exception):
            await guild.ban(member_or_user, reason=reason, delete_message_days=self.delete_message_days)

    async def _attachment_meta(self, a: discord.Attachment) -> Dict[str, Any]:
        stem, ext = _name_parts(a.filename or "")
        meta = {"stem": stem, "ext": ext, "kind": "unknown"}
        ct = getattr(a, "content_type", "") or ""
        try:
            b = await a.read(); meta["kind"] = _sniff_image_kind(b)
        except Exception:
            if "png" in ct: meta["kind"] = "png"
            elif "jpeg" in ct or "jpg" in ct: meta["kind"] = "jpeg"
            elif "gif" in ct: meta["kind"] = "gif"
            elif "webp" in ct: meta["kind"] = "webp"
        mismatch = False
        if meta["kind"] in {"jpeg","png","gif","webp"} and ext:
            if not ((meta["kind"] == ext) or (meta["kind"] == "jpeg" and ext in {"jpg","jpeg"})): mismatch = True
        meta["ext_mismatch"] = mismatch
        return meta

    def _pack_pattern(self, metas: List[Dict[str, Any]]) -> Dict[str, Any]:
        if len(metas) < self.pack_min: return {"matched": False}
        is_img = [(m.get("kind") in self.image_kinds) or (m.get("ext") in self.pack_exts) for m in metas]
        if sum(is_img) < self.pack_min: return {"matched": False}
        nums = []
        for m in metas:
            stem = (m.get("stem") or "").strip().lower()
            if not stem: continue
            md = re.search(r'(?:^|[^0-9])([1-9][0-9]{0,3})$', stem)
            if md: nums.append(int(md.group(1))); continue
            if self.pack_allow_image_prefix and stem.startswith("image"):
                md2 = re.search(r'\((\d{1,4})\)\s*$', stem) or re.search(r'(\d{1,4})\s*$', stem)
                if md2: nums.append(int(md2.group(1)))
        if len(nums) < self.pack_min: return {"matched": False}
        uniq = sorted(set(nums))
        if len(uniq) < self.pack_min: return {"matched": False}
        if self.require_consecutive and (uniq[-1] - uniq[0] + 1 != len(uniq)): return {"matched": False}
        return {"matched": True, "sequence": uniq}

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # --- PublicChatGate pre-send guard (auto-injected) ---
        gate = None
        try:
            gate = self.bot.get_cog("PublicChatGate")
        except Exception:
            pass
        try:
            if message.guild and gate and hasattr(gate, "should_allow_public_reply") and not gate.should_allow_public_reply(message):
                return
        except Exception:
            pass
        # --- end guard ---

        try:
            await self._on_message(message)
        except Exception as e:
            log.exception("PackMime strict error: %s", e)

    async def _on_message(self, message: discord.Message):
        if not self.enabled: return
        if not isinstance(message.channel, discord.abc.GuildChannel): return
        if not getattr(message, "attachments", None): return
        channel = message.channel; member = message.author
        if self.exempt_threads and isinstance(channel, discord.Thread): return
        if self.whitelist_channels and channel.name and channel.name.lower() in self.whitelist_channels: return
        if not isinstance(member, discord.Member): return
        if self.only_roleless and len(member.roles) > 1: return
        names = {r.name.lower() for r in member.roles}; ids = {r.id for r in member.roles}
        if names & self.exempt_role_names or ids & self.exempt_role_ids: return

        metas = [await self._attachment_meta(a) for a in message.attachments]
        pack = self._pack_pattern(metas)
        if not pack.get("matched"): return
        mismatches = sum(1 for m in metas if m.get("ext_mismatch"))
        if mismatches >= self.mime_direct_ban_min_mismatches:
            desc = (f"User: {member.mention} (`{member.id}`)\n"
                    f"Channel: {channel.mention}\n"
                    f"PACK sequence: {pack.get('sequence')}\n"
                    f"MIME mismatches: {mismatches} (>= {self.mime_direct_ban_min_mismatches})")
            await self._log_embed(message.guild, "AUTO-BAN: PACK + MIME mismatch burst", desc, 0xE74C3C, getattr(message, "jump_url", None))
            await self._ban(message.guild, member, "FirstTouch PACK+MIME strict")
        else:
            await self._log_embed(message.guild, "PACK detected (no ban)",
                                  f"User: {member.mention} — sequence: {pack.get('sequence')}", 0xF1C40F, getattr(message, "jump_url", None))
async def setup(bot: commands.Bot):
    await bot.add_cog(FirstTouchAutoBanPackMime(bot))