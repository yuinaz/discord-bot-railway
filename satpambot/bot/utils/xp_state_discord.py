import os, re, json, asyncio, time, logging
from typing import Tuple, Optional

log = logging.getLogger(__name__)

MARKER = os.getenv("XP_STATE_MARKER", "[XP_STATE]")
CHAN_ID = int(os.getenv("XP_STATE_CHANNEL_ID", "0"))
MSG_ID_ENV = os.getenv("XP_STATE_MESSAGE_ID", "").strip()

# Regex untuk ambil JSON pertama di message
RE_JSON = re.compile(r"\{.*\}", re.DOTALL)

class DiscordState:
    def __init__(self):
        self.channel_id = CHAN_ID
        self.marker = MARKER
        self.message_id_str = MSG_ID_ENV or ""
        self._lock = asyncio.Lock()
        self._next_write_ts = 0.0  # throttle
        self._throttle_sec = float(os.getenv("XP_STATE_WRITE_THROTTLE_SEC", "15"))
        self._backoff_sec = 0.0

    async def _get_channel(self, bot):
        ch = None
        if self.channel_id:
            ch = bot.get_channel(self.channel_id)
            if ch is None:
                try:
                    ch = await bot.fetch_channel(self.channel_id)
                except Exception:
                    log.exception("[xp/discord] fetch_channel failed")
        return ch

    async def _find_or_create_message(self, bot, channel):
        # 1) If message id provided, try fetch
        if self.message_id_str:
            try:
                mid = int(self.message_id_str)
                msg = await channel.fetch_message(mid)
                return msg
            except Exception:
                log.warning("[xp/discord] MSG_ID invalid/unreachable, will search pins")

        # 2) Search pinned messages for our marker
        try:
            pins = await channel.pins()
            for m in pins:
                if self.marker in (m.content or ""):
                    self.message_id_str = str(m.id)
                    return m
        except Exception:
            log.exception("[xp/discord] list pins failed")

        # 3) Create new pinned seed message
        try:
            content = f"{self.marker}\n{{\"total\": 0, \"level\": \"TK\", \"updated\": {int(time.time())}}}"
            msg = await channel.send(content)
            try:
                await msg.pin()
            except Exception:
                log.warning("[xp/discord] pin failed; continuing without pin")
            self.message_id_str = str(msg.id)
            log.info("[xp/discord] created new state message id=%s", self.message_id_str)
            return msg
        except Exception:
            log.exception("[xp/discord] create state message failed")
            return None

    async def load(self, bot) -> Tuple[Optional[int], Optional[str]]:
        """Return (total, level) from pinned message. None/None if missing."""
        if not self.channel_id:
            log.warning("[xp/discord] XP_STATE_CHANNEL_ID missing")
            return None, None
        ch = await self._get_channel(bot)
        if not ch:
            return None, None
        msg = await self._find_or_create_message(bot, ch)
        if not msg:
            return None, None
        text = msg.content or ""
        m = RE_JSON.search(text)
        if not m:
            return None, None
        try:
            data = json.loads(m.group(0))
            t = int(data.get("total", 0))
            lvl = str(data.get("level", "TK"))
            return t, lvl
        except Exception:
            log.exception("[xp/discord] parse JSON failed")
            return None, None

    async def save(self, bot, total: int, level: str):
        """Upsert JSON into the pinned message; throttled & with simple backoff."""
        if not self.channel_id:
            return

        async with self._lock:
            now = time.time()
            if now < self._next_write_ts:
                # schedule a delayed retry
                delay = self._next_write_ts - now
                await asyncio.sleep(delay)

            ch = await self._get_channel(bot)
            if not ch:
                return
            msg = await self._find_or_create_message(bot, ch)
            if not msg:
                return

            content = f"{self.marker}\n{{\"total\": {int(total)}, \"level\": \"{level}\", \"updated\": {int(time.time())}}}"
            try:
                await msg.edit(content=content)
                # success: reduce backoff
                self._backoff_sec = 0.0
                self._next_write_ts = time.time() + self._throttle_sec
            except Exception as e:
                # Basic backoff on rate limit or other failures
                self._backoff_sec = min(max(self._backoff_sec * 2, 5.0), 60.0) if self._backoff_sec else 5.0
                self._next_write_ts = time.time() + self._backoff_sec
                log.warning("[xp/discord] save failed (%r), backoff=%.1fs", e, self._backoff_sec)
