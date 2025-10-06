
from __future__ import annotations
import os, logging, time, sqlite3, asyncio
from typing import Optional, List
import discord
from discord.ext import commands, tasks

from ..helpers import upgrade_rules

log = logging.getLogger(__name__)

DEFAULT_OWNER_ID = 228126085160763392  # fallback if env OWNER_USER_ID not set

def _db_path() -> str:
    return os.getenv("NEUROLITE_MEMORY_DB",
        os.path.join(os.path.dirname(__file__), "..","..","..","..","data","memory.sqlite3"))

def _open_db():
    path = _db_path()
    d = os.path.dirname(path)
    if d and not os.path.exists(d):
        try: os.makedirs(d, exist_ok=True)
        except Exception: pass
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    return con

def _ensure_meta(con: sqlite3.Connection):
    con.execute("""CREATE TABLE IF NOT EXISTS learning_progress_meta(
        key TEXT PRIMARY KEY,
        value TEXT
    )""")
    con.commit()

def _get_owner_id(bot: commands.Bot) -> int:
    val = os.getenv("OWNER_USER_ID")
    if val:
        try: return int(val)
        except Exception: pass
    # Try app owner if present
    try:
        app = getattr(bot, "application", None)
        if app and app.owner:  # type: ignore
            return int(app.owner.id)  # type: ignore
    except Exception:
        pass
    return DEFAULT_OWNER_ID

async def _get_owner_dm(bot: commands.Bot) -> Optional[discord.DMChannel]:
    owner_id = _get_owner_id(bot)
    user = bot.get_user(owner_id) or await bot.fetch_user(owner_id)
    if not user:
        return None
    try:
        dm = await user.create_dm()
        return dm
    except Exception:
        return None

def _meta_get(con: sqlite3.Connection, key: str) -> Optional[str]:
    _ensure_meta(con)
    row = con.execute("SELECT value FROM learning_progress_meta WHERE key=?", (key,)).fetchone()
    return row["value"] if row else None

def _meta_set(con: sqlite3.Connection, key: str, val: str):
    _ensure_meta(con)
    con.execute("INSERT INTO learning_progress_meta(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, val))
    con.commit()

class UpgradeAdvisor(commands.Cog):
    """DM owner ketika ada peluang upgrade non-crucial, dan minta izin untuk crucial.
       Anti-spam: cek setiap 12 jam, simpan jejak proposal/ack di DB meta.
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.check_task.start()

    def cog_unload(self):
        try: self.check_task.cancel()
        except Exception: pass

    @tasks.loop(hours=12)
    async def check_task(self):
        await self.bot.wait_until_ready()
        con = _open_db()
        now = int(time.time())

        # Cooldown global (hindari DM spam)
        last = int(_meta_get(con, "upgrade_last_dm_ts") or "0")
        if now - last < 6*3600:  # min 6 jam antar DM
            return

        proposals = upgrade_rules.evaluate(con)
        if not proposals:
            return

        dm = await _get_owner_dm(self.bot)
        if not dm:
            return

        # Kirim satu DM berisi beberapa proposal ringkas
        lines = ["**Neuro-Lite Upgrade Advisor** (auto)\n"]
        for p in proposals[:5]:  # batasi 5 item per DM
            sent_key = f"upgrade_sent:{p['key']}"
            if _meta_get(con, sent_key):
                continue
            lines.append(f"• **{p['title']}** [{p['severity']}{' / crucial' if p.get('crucial') else ''}]")
            lines.append(f"  └ alasan: {p['reason']}")
            # tanda intruksi
            if p.get("crucial"):
                lines.append(f"  └ balas: YA {p['key']} / TIDAK {p['key']}")
            else:
                lines.append(f"  └ balas (opsional): YA {p['key']} untuk izinkan peningkatan opsional")
        if len(lines) <= 1:
            return
        msg = "\n".join(lines)
        try:
            await dm.send(msg)
            _meta_set(con, "upgrade_last_dm_ts", str(now))
            # mark as sent to avoid re-DM
            for p in proposals[:5]:
                _meta_set(con, f"upgrade_sent:{p['key']}", str(now))
        except Exception:
            log.exception("[upgrade] gagal kirim DM owner")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Only listen in owner's DM
        if message.author.bot:
            return
        if not isinstance(message.channel, discord.DMChannel):
            return
        owner_id = _get_owner_id(self.bot)
        if int(message.author.id) != owner_id:
            return

        content = (message.content or "").strip().lower()
        if not content:
            return

        # Expected: "ya <key>" or "tidak <key>"
        verb = None
        if content.startswith("ya "):
            verb = "YA"
            key = content[3:].strip()
        elif content.startswith("tidak "):
            verb = "TIDAK"
            key = content[6:].strip()
        else:
            return

        if not key:
            return

        con = _open_db()
        now = int(time.time())
        if verb == "YA":
            _meta_set(con, f"upgrade_ack:{key}", f"APPROVED:{now}")
            await message.channel.send(f"✅ Upgrade **{key}** disetujui. Bot akan menyiapkan langkahnya (non-crucial otomatis; crucial menunggu konfirmasi lanjutan).")
        else:
            _meta_set(con, f"upgrade_ack:{key}", f"REJECTED:{now}")
            await message.channel.send(f"🛑 Upgrade **{key}** ditolak. Tidak ada perubahan yang diterapkan.")

async def setup(bot: commands.Bot):
    await bot.add_cog(UpgradeAdvisor(bot))
