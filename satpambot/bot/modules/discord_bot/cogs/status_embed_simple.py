# satpambot/bot/modules/discord_bot/cogs/status_embed_simple.py
import json, os
from pathlib import Path
from datetime import datetime, timezone, timedelta

import discord
from discord.ext import commands, tasks

WIB = timezone(timedelta(hours=7))
STATE_FILE = Path(os.getenv("DATA_DIR","data")) / "status_embed_last.json"
CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID_RAW", "0"))  # atau gunakan channel status khusus

def _read_last():
    try:
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}

def _write_last(d):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")

class StatusEmbedSimple(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.updater.start()

    def cog_unload(self):
        try:
            self.updater.cancel()
        except Exception:
            pass

    @tasks.loop(minutes=30)
    async def updater(self):
        await self.bot.wait_until_ready()
        ch_id = CHANNEL_ID
        if ch_id <= 0:
            return
        ch = self.bot.get_channel(ch_id)
        if not ch:
            try:
                ch = await self.bot.fetch_channel(ch_id)
            except Exception:
                return

        # data status (contoh sederhana)
        presence = "presence=online"
        uptime = "uptime=?"
        now_wib = datetime.now(WIB)
        ts_utc = datetime.utcnow().replace(tzinfo=timezone.utc)

        # embed
        emb = discord.Embed(title="SatpamBot Status", description="Status ringkas bot.")
        emb.add_field(name="Presence", value=presence, inline=True)
        emb.add_field(name="Uptime", value=uptime, inline=True)
        emb.set_footer(text=f"SATPAMBOT_STATUS_V1 • {now_wib.strftime('%Y-%m-%d %H:%M WIB')}")
        emb.timestamp = ts_utc  # Discord akan tampilkan timestamp; viewer melihat dalam lokalnya

        # konten header (baris atas) — ini yang kamu pakai di screenshot
        header = f"✅ Online sebagai {self.bot.user} | `{presence}` | `{uptime}`"

        state = _read_last()
        msg_id = int(state.get("message_id") or 0)

        try:
            if msg_id:
                try:
                    msg = await ch.fetch_message(msg_id)
                    await msg.edit(content=header, embed=emb)
                except discord.NotFound:
                    # pesan lama hilang — kirim baru
                    m = await ch.send(content=header, embed=emb)
                    _write_last({"message_id": m.id})
            else:
                m = await ch.send(content=header, embed=emb)
                _write_last({"message_id": m.id})
        except Exception:
            # kalau gagal edit & kirim, jangan crash loop
            pass

    @updater.before_loop
    async def before_updater(self):
        await self.bot.wait_until_ready()

# loader untuk shim_runner
def setup(bot: commands.Bot):
    bot.add_cog(StatusEmbedSimple(bot))
