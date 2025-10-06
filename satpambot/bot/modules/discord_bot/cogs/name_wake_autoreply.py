
from __future__ import annotations
import os, re, time, logging, inspect
from typing import Optional
import discord
from discord.ext import commands
from ..helpers import mood_state

log = logging.getLogger(__name__)

def _names_pattern() -> re.Pattern:
    pat = os.getenv("WAKE_NAMES", "leina|satpamleina")
    return re.compile(rf"^\s*(?:{pat})\s*[:,\-]?\s*(.*)$", re.IGNORECASE|re.UNICODE)

def _is_disabled() -> bool:
    return os.getenv("WAKE_NAME_AUTO", "1") == "0"

def _allow_in_logs() -> bool:
    return os.getenv("WAKE_ALLOW_IN_LOG", "0") == "1"

WAKE_RE = _names_pattern()

ANGRY_WORDS = {"angry","marah","rage","geram","kesel","怒","wrath","murka","angy"}

class NameWakeAutoReply(commands.Cog):
    """Auto-reply tanpa @mention + persona/mood (tsundere)."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._last_user: dict[int, float] = {}
        self._last_ch: dict[int, float] = {}
        self._min_user = int(os.getenv("WAKE_MIN_SEC_USER", "6"))
        self._min_ch = int(os.getenv("WAKE_MIN_SEC_CH", "3"))
        self._angry_cd: dict[int, float] = {}

    def _cooldown_ok(self, uid: int, cid: int) -> bool:
        now = time.monotonic()
        if now - self._last_user.get(uid, 0.0) < self._min_user: return False
        if now - self._last_ch.get(cid, 0.0) < self._min_ch: return False
        self._last_user[uid] = now
        self._last_ch[cid] = now
        return True

    def _channel_allowed(self, ch: discord.abc.Messageable) -> bool:
        name = (getattr(ch, "name", "") or "").lower()
        if not _allow_in_logs() and ("log-botphising" in name or "progress" in name):
            return False
        return True

    async def _delegate_to_neuro(self, message: discord.Message, text: str) -> bool:
        cog = self.bot.get_cog("ChatNeuroLite")
        if not cog: return False
        for cand in ("handle_query", "reply_message", "inference_reply", "chat", "respond"):
            fn = getattr(cog, cand, None)
            if fn and inspect.iscoroutinefunction(fn):
                try:
                    await fn(message, text)
                    return True
                except TypeError:
                    try:
                        await fn(message)
                        return True
                    except Exception:
                        continue
                except Exception:
                    log.exception("[wake] delegate to ChatNeuroLite failed via %s", cand)
                    return False
        return False

    def _pick_angry_sticker(self, guild: Optional[discord.Guild]) -> Optional[discord.GuildSticker]:
        if not guild: return None
        try:
            for st in getattr(guild, "stickers", []):
                name = (st.name or "").lower()
                if any(w in name for w in ANGRY_WORDS):
                    return st
        except Exception:
            pass
        return None

    def _fallback_reply(self, text: str, mood: str) -> str:
        t = (text or "").strip()
        if mood == "annoyed":
            base = "E-eh!? Aku lagi belajar lho… jangan ganggu! 😤"
            if t:
                base += f" (\"{t}\")"
            return base + " *hmpf* www"
        if not t:
            return "Hmm? Ada apa? Jangan ngetag aku sembarangan ya~ www"
        if t.endswith("?"):
            return f"{t}\nJawabanku sebentar ya—aku mikir dulu, jangan manja~ 😉"
        return f"Oke noted: “{t}”. Ayo bahas pelan-pelan~"

    async def _maybe_angry_express(self, message: discord.Message, mood: str):
        if mood != "annoyed": return
        cid = int(message.channel.id)
        now = time.monotonic()
        if now - self._angry_cd.get(cid, 0.0) < 60.0:
            return
        self._angry_cd[cid] = now
        # try sticker first, fallback emoji reaction
        st = self._pick_angry_sticker(getattr(message.guild, "guild", message.guild))
        if st:
            try:
                await message.channel.send(stickers=[st])
                return
            except Exception:
                pass
        try:
            await message.add_reaction("😤")
        except Exception:
            pass

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if _is_disabled(): return
        if message.author.bot: return
        if not isinstance(message.channel, (discord.TextChannel, discord.Thread, discord.DMChannel)):
            return
        if not self._channel_allowed(message.channel): return
        content = (message.content or "")
        m = WAKE_RE.match(content)
        if not m: return

        if message.reference and isinstance(message.reference.resolved, discord.Message):
            if getattr(message.reference.resolved.author, "id", None) == getattr(self.bot.user, "id", None):
                return

        if not self._cooldown_ok(int(message.author.id), int(message.channel.id)): return

        text = m.group(1).strip()
        learning = mood_state.is_learning_active(180)
        mood = "annoyed" if learning else mood_state.get_mood()

        # Immediate small expressive action if annoyed
        await self._maybe_angry_express(message, mood)

        # Try delegate to main chat cog; else fallback persona respecting mood
        async with message.channel.typing():
            if await self._delegate_to_neuro(message, text):
                return
            try:
                await message.reply(self._fallback_reply(text, mood), mention_author=False)
            except Exception:
                log.exception("[wake] reply failed")

async def setup(bot: commands.Bot):
    # unload old one if exists (to ensure upgrade takes effect)
    try:
        old = bot.get_cog("NameWakeAutoReply")
        if old:
            await bot.remove_cog("NameWakeAutoReply")
    except Exception:
        pass
    await bot.add_cog(NameWakeAutoReply(bot))
