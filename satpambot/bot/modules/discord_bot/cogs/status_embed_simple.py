from __future__ import annotations
import os, asyncio, time
from datetime import datetime, timezone, timedelta
import discord
from discord.ext import commands, tasks

# WIB +7
TZ_WIB = timezone(timedelta(hours=7), name="WIB")

class StatusEmbedSimple(commands.Cog):
    """
    Post 1 pesan status lalu EDIT berkala (seperti screenshot).
    ENV:
      - STATUS_CHANNEL_ID   : channel ID target (wajib)
      - STATUS_UPDATE_SECS  : interval update (default 30s)
      - DATA_DIR            : lokasi file msg_id (default 'data/')
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.ch_id = int(os.getenv("STATUS_CHANNEL_ID", "0") or 0)
        self.interval = int(os.getenv("STATUS_UPDATE_SECS", "30") or 30)
        if self.interval < 10: self.interval = 10
        data_dir = os.getenv("DATA_DIR", "data")
        os.makedirs(data_dir, exist_ok=True)
        self.msg_id_file = os.path.join(data_dir, "status_msg_id.txt")
        # start time untuk hitung uptime
        self.start_ts = getattr(bot, "start_time", None) or time.time()
        # jalanin loop
        self.update_loop.change_interval(seconds=self.interval)
        self.update_loop.start()

    # ---------- utils ----------
    def _save_msg_id(self, mid: int):
        try:
            with open(self.msg_id_file, "w", encoding="utf-8") as f:
                f.write(str(mid))
        except Exception:
            pass

    def _load_msg_id(self) -> int | None:
        try:
            with open(self.msg_id_file, "r", encoding="utf-8") as f:
                v = (f.read() or "").strip()
                return int(v) if v else None
        except Exception:
            return None

    def _fmt_uptime(self) -> str:
        secs = int(max(0, time.time() - (self.start_ts or time.time())))
        m, s = divmod(secs, 60)
        h, m = divmod(m, 60)
        d, h = divmod(h, 24)
        if d:  return f"{d}d {h}h {m}m"
        if h:  return f"{h}h {m}m {s}s"
        if m:  return f"{m}m {s}s"
        return f"{s}s"

    def _presence_text(self) -> str:
        try:
            st = self.bot.status  # online/idle/dnd/offline
        except Exception:
            st = discord.Status.online if self.bot.is_ready() else discord.Status.offline
        return str(st)

    def _embed(self) -> discord.Embed:
        user = self.bot.user
        name = f"{user.name}#{user.discriminator}" if user else "Unknown"
        emb = discord.Embed(
            title="SatpamBot Status",
            description="Status ringkas bot.",
            color=0x2ecc71,
            timestamp=datetime.now(TZ_WIB)  # footer “Today at …”
        )
        emb.add_field(name="Akun", value=name, inline=False)
        emb.add_field(name="Presence", value=f"`{self._presence_text()}`", inline=True)
        emb.add_field(name="Uptime", value=self._fmt_uptime(), inline=True)
        emb.set_footer(text="SATPAMBOT_STATUS_V1")
        if user and user.display_avatar:
            emb.set_thumbnail(url=user.display_avatar.url)
        return emb

    # ---------- loop ----------
    @tasks.loop(seconds=1800)
    async def update_loop(self):
        await self.bot.wait_until_ready()
        if not self.ch_id:
            return  # belum dikonfigurasi

        # cari channel
        ch = self.bot.get_channel(self.ch_id)
        if not isinstance(ch, (discord.TextChannel, discord.Thread)):
            try:
                ch = await self.bot.fetch_channel(self.ch_id)  # type: ignore
            except Exception:
                return

        # siapkan content + embed
        content = f"✅ Online sebagai **{self.bot.user}** | `presence={self._presence_text()}` | `uptime={self._fmt_uptime()}`"
        emb = self._embed()

        # edit pesan lama kalau ada; kalau tidak ada, kirim baru
        msg_id = self._load_msg_id()
        try:
            if msg_id:
                try:
                    msg = await ch.fetch_message(msg_id)  # type: ignore
                    await msg.edit(content=content, embed=emb)
                    return
                except Exception:
                    pass
            msg = await ch.send(content=content, embed=emb)
            self._save_msg_id(msg.id)
        except Exception as e:
            print(f"[status_embed_simple] update failed: {e}")

    @update_loop.before_loop
    async def _before(self):
        await self.bot.wait_until_ready()
        await asyncio.sleep(5)

# loader kompatibel
async def setup(bot: commands.Bot):
    await bot.add_cog(StatusEmbedSimple(bot))

def setup(bot: commands.Bot):
    bot.add_cog(StatusEmbedSimple(bot))
