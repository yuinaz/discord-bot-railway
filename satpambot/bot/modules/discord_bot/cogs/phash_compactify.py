# -*- coding: utf-8 -*-
"""
phash_compactify.py (v1c - context menu top-level, keep original)
- Context menu "Compact pHash" is defined at top-level (discord.py rule).
- Creates compact, paginated embed with persistent buttons (Next/Prev etc.).
- Original message is NOT deleted (acts as log).
- Slash: /phash_compact_post
"""
from __future__ import annotations
import re, json, io, os
from typing import List, Tuple, Optional

import discord
from discord.ext import commands
from discord import app_commands

PAGE_SIZE = 20
ATTACH_NAME = "phash_page_data.json"

CANDIDATE_PATHS = [
    os.getenv("PHISH_PHASH_STORE"),
    os.getenv("PHASH_STORE"),
    "satpambot/data/phash_index.json",
    "data/phash_index.json",
]

def _extract_json_blob(text: str) -> Optional[str]:
    if not text:
        return None
    text = text.strip()
    if text.startswith("```") and text.endswith("```"):
        text = text.strip("`").strip()
    m = re.search(r"(\{.*\}|\[.*\])", text, flags=re.S)
    if not m:
        return None
    return m.group(1)

def _parse_hashes_from_json(blob: str) -> Optional[List[str]]:
    try:
        data = json.loads(blob)
    except Exception:
        return None
    if isinstance(data, dict):
        if "phash" in data and isinstance(data["phash"], list):
            return [str(x) for x in data["phash"]]
        if "hashes" in data and isinstance(data["hashes"], list):
            return [str(x) for x in data["hashes"]]
    if isinstance(data, list):
        return [str(x) for x in data]
    return None

def _load_from_file_paths() -> Tuple[List[str], Optional[str]]:
    for p in CANDIDATE_PATHS:
        if not p:
            continue
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            items = data.get("phash") or data.get("hashes") or []
            if isinstance(items, list):
                return [str(x) for x in items], p
        except FileNotFoundError:
            continue
        except Exception:
            continue
    return [], None

def _pages_from_items(items: List[str], page_size: int = PAGE_SIZE) -> List[str]:
    pages = []
    for i in range(0, len(items), page_size):
        chunk = items[i:i+page_size]
        body = "```\n" + "\n".join(chunk) + "\n```"
        if len(body) > 4000:
            chunk = items[i:i+15]
            body = "```\n" + "\n".join(chunk) + "\n```"
        pages.append(body)
    return pages or ["*(empty)*"]

def _embed_for_page(pages: List[str], index: int) -> discord.Embed:
    index = max(0, min(index, len(pages)-1))
    e = discord.Embed(
        title="pHash DB (compact)",
        description=pages[index],
        color=0x2e8b57
    )
    e.set_footer(text=f"Page {index+1}/{len(pages)}")
    return e

class PhashPersistentView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def _read_items_from_message(self, message: discord.Message) -> List[str]:
        att = None
        for a in message.attachments:
            if a.filename == ATTACH_NAME:
                att = a
                break
        if not att:
            return []
        try:
            data = await att.read()
            payload = json.loads(data.decode("utf-8"))
            if isinstance(payload, list):
                return [str(x) for x in payload]
            if isinstance(payload, dict) and "phash" in payload and isinstance(payload["phash"], list):
                return [str(x) for x in payload["phash"]]
        except Exception:
            return []
        return []

    def _current_index_from_embed(self, embed: discord.Embed) -> int:
        if not embed or not embed.footer or not embed.footer.text:
            return 0
        txt = embed.footer.text.strip().lower()
        m = re.search(r"page\s+(\d+)\s*/\s*(\d+)", txt)
        if not m:
            return 0
        try:
            x = int(m.group(1)); y = int(m.group(2))
            return max(1, min(x, y)) - 1
        except Exception:
            return 0

    async def _flip(self, interaction: discord.Interaction, delta: int = 0, absolute: int = None):
        msg = interaction.message
        if not msg or not msg.embeds:
            return await interaction.response.defer()
        items = await self._read_items_from_message(msg)
        if not items:
            return await interaction.response.send_message("No page data found.", ephemeral=True)
        pages = _pages_from_items(items)
        cur = self._current_index_from_embed(msg.embeds[0])
        new_idx = (absolute if absolute is not None else cur + delta)
        new_idx = max(0, min(new_idx, len(pages)-1))
        await interaction.response.edit_message(embed=_embed_for_page(pages, new_idx), view=self)

    @discord.ui.button(label="≪ First", style=discord.ButtonStyle.secondary, custom_id="phash:first")
    async def first(self, interaction: discord.Interaction, _: discord.ui.Button):
        await self._flip(interaction, absolute=0)

    @discord.ui.button(label="‹ Prev", style=discord.ButtonStyle.secondary, custom_id="phash:prev")
    async def prev(self, interaction: discord.Interaction, _: discord.ui.Button):
        await self._flip(interaction, delta=-1)

    @discord.ui.button(label="Next ›", style=discord.ButtonStyle.secondary, custom_id="phash:next")
    async def next(self, interaction: discord.Interaction, _: discord.ui.Button):
        await self._flip(interaction, delta=1)

    @discord.ui.button(label="Last ≫", style=discord.ButtonStyle.secondary, custom_id="phash:last")
    async def last(self, interaction: discord.Interaction, _: discord.ui.Button):
        await self._flip(interaction, absolute=10**9)

    @discord.ui.button(label="Download JSON", style=discord.ButtonStyle.success, custom_id="phash:download")
    async def download(self, interaction: discord.Interaction, _: discord.ui.Button):
        msg = interaction.message
        if not msg:
            return await interaction.response.defer()
        att = None
        for a in msg.attachments:
            if a.filename == ATTACH_NAME:
                att = a
                break
        if not att:
            return await interaction.response.send_message("No page data found.", ephemeral=True)
        try:
            data = await att.read()
        except Exception as e:
            return await interaction.response.send_message(f"Read error: {e}", ephemeral=True)
        buf = io.BytesIO(data); buf.seek(0)
        await interaction.response.send_message(
            content="Full `phash` JSON:",
            file=discord.File(buf, filename="phash_index.json"),
            ephemeral=True
        )

# --- Top-level Context Menu callback (discord.py requirement) ---
async def compact_message_handler(interaction: discord.Interaction, message: discord.Message):
    source_text = message.content or ""
    if not source_text and message.embeds:
        source_text = (message.embeds[0].description or "")

    blob = _extract_json_blob(source_text)
    if not blob:
        return await interaction.response.send_message("❌ No JSON found in that message.", ephemeral=True)

    items = _parse_hashes_from_json(blob)
    if not items:
        return await interaction.response.send_message("❌ Could not parse a pHash list from that message.", ephemeral=True)

    pages = _pages_from_items(items)
    payload = json.dumps(items, ensure_ascii=False).encode("utf-8")
    file = discord.File(io.BytesIO(payload), filename=ATTACH_NAME)

    view = PhashPersistentView()
    embed = _embed_for_page(pages, 0)
    await interaction.response.send_message(
        content=f"**pHash compact view** (from message {message.id})",
        embed=embed,
        view=view,
        file=file,
        ephemeral=False
    )
    # NOTE: do not delete original message (keep log)

class PhashCompactify(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        bot.add_view(PhashPersistentView())

    @app_commands.command(name="phash_compact_post", description="Post pHash DB as a compact pager")
    async def phash_compact_post(self, interaction: discord.Interaction):
        items, src = _load_from_file_paths()
        if not items:
            return await interaction.response.send_message("No pHash data file found.", ephemeral=True)

        pages = _pages_from_items(items)
        payload = json.dumps(items, ensure_ascii=False).encode("utf-8")
        file = discord.File(io.BytesIO(payload), filename=ATTACH_NAME)

        view = PhashPersistentView()
        embed = _embed_for_page(pages, 0)
        await interaction.response.send_message(
            content=f"**pHash compact view** (source: `{src}`)",
            embed=embed,
            view=view,
            file=file,
            ephemeral=False
        )

async def setup(bot: commands.Bot):
    # load cog for slash command + persistent view
    await bot.add_cog(PhashCompactify(bot))

    # register Context Menu at top-level
    gid = os.getenv("GUILD_METRICS_ID")
    if gid and gid.isdigit():
        ctx = app_commands.ContextMenu(name="Compact pHash", callback=compact_message_handler, guild=discord.Object(id=int(gid)))
    else:
        ctx = app_commands.ContextMenu(name="Compact pHash", callback=compact_message_handler)
    bot.tree.add_command(ctx)
