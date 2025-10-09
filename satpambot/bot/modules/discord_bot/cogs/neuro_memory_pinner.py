# -*- coding: utf-8 -*-
from __future__ import annotations
import asyncio, json, logging
from pathlib import Path
from typing import Optional

import discord
from discord.ext import commands, tasks

from satpambot.bot.modules.discord_bot.helpers.thread_utils import ensure_neuro_thread, DEFAULT_THREAD_NAME
from satpambot.bot.modules.discord_bot.helpers.message_keeper import get_keeper

log = logging.getLogger(__name__)

MEM_PATHS = [
    Path("data/learn_progress_junior.json"),
    # Add more state files here if needed (e.g., data/memory_state.json)
]
KEEPER_KEY = "[neuro-lite:memory]"

def _load_memory_json() -> str:
    merged = {}
    for p in MEM_PATHS:
        try:
            if p.exists():
                d = json.loads(p.read_text(encoding="utf-8"))
                merged[p.name] = d
        except Exception as e:
            merged[p.name] = {"error": str(e)}
    if not merged:
        merged = {"status": "no memory files found"}
    # Pretty JSON in a code fence so it's readable
    return "```json\n" + json.dumps(merged, ensure_ascii=False, indent=2) + "\n```"

class NeuroLiteMemoryPinner(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._last_blob = None
        self.ensure_once.start()
        self.watch_task.start()

    def cog_unload(self):
        for t in (self.ensure_once, self.watch_task):
            try: t.cancel()
            except Exception: pass

    async def _upsert_and_pin(self) -> Optional[discord.Message]:
        th = await ensure_neuro_thread(self.bot, DEFAULT_THREAD_NAME)
        if not th:
            log.warning("[memory_pinner] cannot ensure neuro thread")
            return None
        keeper = get_keeper(self.bot)
        blob = _load_memory_json()
        try:
            msg = await keeper.update(th, key=KEEPER_KEY, content="**NEURO-LITE MEMORY**\n" + blob)
            # Pin it (ignore if already pinned or perms missing)
            try:
                await msg.pin(reason="Neuro-Lite memory keeper")
            except Exception:
                pass
            self._last_blob = blob
            log.info("[memory_pinner] memory keeper upserted & pinned in thread #%s", getattr(th, "name", "?"))
            return msg
        except Exception as e:
            log.warning("[memory_pinner] update failed: %s", e)
            return None

    @tasks.loop(count=1)
    async def ensure_once(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(1.0)
        await self._upsert_and_pin()

    @tasks.loop(minutes=10)
    async def watch_task(self):
        await self.bot.wait_until_ready()
        try:
            blob = _load_memory_json()
            if blob != self._last_blob:
                await self._upsert_and_pin()
        except Exception:
            log.exception("[memory_pinner] watch loop error")

    @ensure_once.before_loop
    async def _before(self):
        await self.bot.wait_until_ready()

    @watch_task.before_loop
    async def _before_watch(self):
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot):
    await bot.add_cog(NeuroLiteMemoryPinner(bot))
