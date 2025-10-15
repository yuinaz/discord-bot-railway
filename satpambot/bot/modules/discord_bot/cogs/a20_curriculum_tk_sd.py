# a20_curriculum_tk_sd.py  (JSON-based, runtime XP bridge, no ENV)
# Curriculum manager (safe-by-default) dengan multi-criteria gate:
# - Target XP (persist di config/curriculum.json)
# - Minimal hari berjalan (min_days)
# - Minimal shadow accuracy 7d (min_acc) jika tersedia
# - DM-only (owner) commands untuk mengatur semuanya (persist ke JSON)
# - Report harian ke channel report dari config (bukan publik)

import json
import logging
import datetime as dt
from pathlib import Path
from typing import Any, Dict, Optional
from discord.ext import commands, tasks

log = logging.getLogger(__name__)

# -------------------- lokasi data & default --------------------
CONFIG_PATH = Path("config/curriculum.json")
DATA_DIR = Path("data/learning")
PROGRESS_FILE = DATA_DIR / "progress.json"
STATS_FILE = DATA_DIR / "shadow_stats.json"  # opsional, untuk sumber akurasi bila ada

DEFAULT_CFG: Dict[str, Any] = {
    "enabled": True,
    "target_xp": 2000,
    "min_days": 7,
    "min_acc": 95.0,          # persen
    "report_hhmm": "2355",    # jam lokal (WIB default)
    "tz_offset_minutes": 420, # Asia/Jakarta (+0700)
    "report_channel_id": None # set via DM: `curriculum set channel <id | #name>`
}

CHECK_MINUTES = 10  # cadence loop (menit)

# -------------------- util config --------------------
def _ensure_dir(p: Path):
    p.parent.mkdir(parents=True, exist_ok=True)

def _load_cfg() -> Dict[str, Any]:
    try:
        if CONFIG_PATH.exists():
            return {**DEFAULT_CFG, **json.loads(CONFIG_PATH.read_text(encoding="utf-8"))}
    except Exception as e:
        log.warning("curriculum: gagal load config: %r", e)
    return DEFAULT_CFG.copy()

def _save_cfg(cfg: Dict[str, Any]) -> None:
    try:
        _ensure_dir(CONFIG_PATH)
        CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        log.warning("curriculum: gagal save config: %r", e)

# -------------------- time helpers --------------------
def _now_local(tz_minutes: int) -> dt.datetime:
    return dt.datetime.utcnow() + dt.timedelta(minutes=tz_minutes)

def _parse_hhmm(s: str) -> dt.time:
    s = (s or "2355").strip().replace(":", "")
    if len(s) not in (3, 4):
        s = "2355"
    if len(s) == 3:
        h = int(s[0]); m = int(s[1:])
    else:
        h = int(s[:2]); m = int(s[2:])
    h = max(0, min(23, h)); m = max(0, min(59, m))
    return dt.time(hour=h, minute=m)

# -------------------- sumber data XP & akurasi --------------------
def _probe_total_xp_module() -> int:
    # Ambil TOTAL_XP dari modul bila tersedia; fallback ke progress.json.
    try:
        from satpambot.bot.modules.discord_bot.cogs.learning_passive_observer import TOTAL_XP  # type: ignore
        return int(TOTAL_XP)
    except Exception:
        pass
    try:
        if PROGRESS_FILE.exists():
            obj = json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
            return int(obj.get("xp_total", 0))
    except Exception:
        pass
    return 0

def _probe_total_xp_runtime(bot) -> Optional[int]:
    # Cari di instance cog yang sedang jalan (lebih akurat daripada modul).
    if bot is None:
        return None
    try:
        for name, cog in bot.cogs.items():
            # kandidat nama cog pembelajar pasif
            if any(k in name.lower() for k in ("learning", "passive", "observer")):
                for attr in ("TOTAL_XP", "total_xp", "xp_total", "xp"):
                    if hasattr(cog, attr):
                        v = int(getattr(cog, attr))
                        if v >= 0:
                            return v
        # fallback: brute-force semua cog
        for cog in bot.cogs.values():
            for attr in ("TOTAL_XP", "total_xp", "xp_total", "xp"):
                if hasattr(cog, attr):
                    v = int(getattr(cog, attr))
                    if v >= 0:
                        return v
    except Exception:
        pass
    return None

def _probe_accuracy() -> Optional[float]:
    # Ambil akurasi 7d dari modul lain atau dari data/learning/shadow_stats.json.
    for path in [
        "satpambot.bot.modules.discord_bot.cogs.learning_passive_observer",
        "satpambot.ml.guard_hooks",
    ]:
        try:
            mod = __import__(path, fromlist=["*"])
            for name in ("ACCURACY_7D", "SHADOW_ACCURACY_7D", "SHADOW_ACC_7D", "ACC_7D"):
                if hasattr(mod, name):
                    v = float(getattr(mod, name))
                    if 0 <= v <= 100: return v
        except Exception:
            pass
    try:
        if STATS_FILE.exists():
            data = json.loads(STATS_FILE.read_text(encoding="utf-8"))
            for k in ("acc_7d", "shadow_acc_7d", "accuracy_7d"):
                if k in data:
                    v = float(data[k])
                    if 0 <= v <= 100: return v
    except Exception:
        pass
    return None

# -------------------- Cog utama --------------------
class CurriculumTKSD(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cfg = _load_cfg()
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if not PROGRESS_FILE.exists():
            PROGRESS_FILE.write_text(
                json.dumps({
                    "xp_total": 0,
                    "created_at": _now_local(self.cfg["tz_offset_minutes"]).strftime("%Y-%m-%d"),
                    "today": "",
                    "daily": {},
                    "weekly": {},
                    "monthly": {},
                }, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        self._last_report_day: Optional[str] = None
        self._loop.start()

    # -------- owner helpers --------
    def _owner_id(self) -> Optional[int]:
        try:
            app = self.bot.application
            if app and app.owner:
                return int(app.owner.id)
        except Exception:
            pass
        return None

    async def _is_owner_dm(self, message) -> bool:
        if getattr(message, "guild", None) is not None:
            return False
        oid = self._owner_id()
        return (oid is not None) and (getattr(message.author, "id", None) == oid)

    async def _dm_owner(self, text: str):
        oid = self._owner_id()
        if not oid:
            return
        try:
            user = await self.bot.fetch_user(oid)
            if user:
                await user.send(text)
        except Exception:
            pass

    # -------- channel report --------
    def _report_channel(self):
        cid = self.cfg.get("report_channel_id")
        if cid:
            try:
                ch = self.bot.get_channel(int(cid))
                if ch: return ch
            except Exception:
                pass
        # fallback: cari channel bernama log-botphising / variasi
        target_names = [
            "log-botphising", "log-botphishing", "log_botphising",
            "log_botphishing", "log-phish", "log_phish"
        ]
        try:
            for g in self.bot.guilds:
                for ch in getattr(g, "text_channels", []):
                    nm = (getattr(ch, "name", "") or "").lower()
                    if any(nm == t for t in target_names):
                        self.cfg["report_channel_id"] = int(ch.id)
                        _save_cfg(self.cfg)
                        return ch
        except Exception:
            pass
        return None

    # -------- core loop --------
    @tasks.loop(minutes=CHECK_MINUTES)
    async def _loop(self):
        if not bool(self.cfg.get("enabled", True)):
            return

        tz = int(self.cfg.get("tz_offset_minutes", 420))
        local_now = _now_local(tz)
        day_key = local_now.strftime("%Y-%m-%d")
        week_key = f"{local_now.isocalendar().year}-W{local_now.isocalendar().week:02d}"
        month_key = local_now.strftime("%Y-%m")

        # muat/simpan progres
        try:
            obj = json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
        except Exception:
            obj = {"xp_total": 0, "created_at": _now_local(tz).strftime("%Y-%m-%d"),
                   "today": "", "daily": {}, "weekly": {}, "monthly": {}}

        # --- XP bridge: runtime cog > module > file ---
        cur_xp = _probe_total_xp_runtime(self.bot)
        if cur_xp is None:
            cur_xp = _probe_total_xp_module()
        obj["xp_total"] = max(int(obj.get("xp_total", 0)), int(cur_xp))  # monotonic
        obj["today"] = day_key
        obj["daily"][day_key] = obj["xp_total"]
        obj["weekly"][week_key] = obj["xp_total"]
        obj["monthly"][month_key] = obj["xp_total"]
        _ensure_dir(PROGRESS_FILE)
        PROGRESS_FILE.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

        target = max(1, int(self.cfg.get("target_xp", 2000)))
        pct = int(min(100, round((obj["xp_total"] / target) * 100)))
        acc = _probe_accuracy()  # None jika tidak ada
        # hitung hari sejak start
        try:
            d0 = dt.datetime.strptime(obj.get("created_at", day_key), "%Y-%m-%d").date()
        except Exception:
            d0 = local_now.date()
        days = max(0, (local_now.date() - d0).days)

        ready = (pct >= 100) and (days >= int(self.cfg.get("min_days", 7))) and (acc is None or acc >= float(self.cfg.get("min_acc", 95.0)))

        # Daily report pada HHMM
        hhmm = _parse_hhmm(str(self.cfg.get("report_hhmm", "2355")))
        if self._last_report_day != day_key and local_now.hour == hhmm.hour and abs(local_now.minute - hhmm.minute) <= (CHECK_MINUTES // 2):
            ch = self._report_channel()
            if ch:
                msg = (
                    f"**Curriculum TK→SD** — {day_key}\n"
                    f"• XP: {obj['xp_total']} ({pct}%) target {target}\n"
                    f"• Days: {days}/{self.cfg.get('min_days', 7)}\n"
                    f"• Acc7d: {'N/A' if acc is None else f'{acc:.1f}%'} (min {self.cfg.get('min_acc', 95.0)}%)\n"
                    f"• Ready: {'✅' if ready else '❌'}"
                )
                try:
                    await ch.send(msg)
                except Exception:
                    pass
            self._last_report_day = day_key

        # Notify owner kalau semua kriteria terpenuhi
        if ready:
            await self._dm_owner("✅ Curriculum TK→SD: semua kriteria terpenuhi (XP, hari minimal, dan akurasi). Silakan unlock publik jika diizinkan.")

    @_loop.before_loop
    async def _wait_ready(self):
        try:
            await self.bot.wait_until_ready()
        except Exception:
            pass

    # -------------------- DM commands (owner-only) --------------------
    @commands.Cog.listener()
    async def on_message(self, message):
        if not await self._is_owner_dm(message):
            return
        content = (message.content or "").strip()
        low = content.lower()

        async def reply(text: str):
            try:
                await message.channel.send(text)
            except Exception:
                pass

        if low in ("curriculum help", "kurikulum help", "help curriculum"):
            await reply(
                "Perintah:\n"
                "- `curriculum status`\n"
                "- `curriculum set target <xp>`\n"
                "- `curriculum set min_days <n>`\n"
                "- `curriculum set min_acc <percent>`\n"
                "- `curriculum set hhmm <HHMM>`\n"
                "- `curriculum set tz <+/-HHMM | minutes>`\n"
                "- `curriculum set channel <id | #name>`\n"
                "- `curriculum report now`\n"
                "- `curriculum enable|disable`"
            )
            return

        if low in ("curriculum status", "kurikulum status"):
            try:
                obj = json.loads(PROGRESS_FILE.read_text(encoding="utf-8")) if PROGRESS_FILE.exists() else {"xp_total": 0, "created_at": _now_local(self.cfg["tz_offset_minutes"]).strftime("%Y-%m-%d")}
            except Exception:
                obj = {"xp_total": 0, "created_at": _now_local(self.cfg["tz_offset_minutes"]).strftime("%Y-%m-%d")}
            # gunakan runtime bridge juga untuk status
            xp_run = _probe_total_xp_runtime(self.bot)
            xp = int(obj.get("xp_total", 0))
            if xp_run is not None:
                xp = max(xp, int(xp_run))
            target = max(1, int(self.cfg.get("target_xp", 2000)))
            pct = int(min(100, round((xp / target) * 100)))
            acc = _probe_accuracy()
            try:
                d0 = dt.datetime.strptime(obj.get("created_at"), "%Y-%m-%d").date()
            except Exception:
                d0 = _now_local(self.cfg["tz_offset_minutes"]).date()
            days = max(0, (_now_local(self.cfg["tz_offset_minutes"]).date() - d0).days)
            await reply(f"TK→SD status:\n• XP {xp} ({pct}%) target {target}\n• Days {days}/{self.cfg.get('min_days', 7)}\n• Acc7d {'N/A' if acc is None else f'{acc:.1f}%'} (min {self.cfg.get('min_acc', 95.0)}%)")
            return

        if low.startswith("curriculum set target"):
            try:
                v = int(low.split()[-1])
                self.cfg["target_xp"] = max(1, v)
                _save_cfg(self.cfg)
                await reply(f"OK: target_xp={self.cfg['target_xp']}")
            except Exception:
                await reply("Format: `curriculum set target 2000`")
            return

        if low.startswith("curriculum set min_days"):
            try:
                v = int(low.split()[-1])
                self.cfg["min_days"] = max(0, v)
                _save_cfg(self.cfg)
                await reply(f"OK: min_days={self.cfg['min_days']}")
            except Exception:
                await reply("Format: `curriculum set min_days 7`")
            return

        if low.startswith("curriculum set min_acc"):
            try:
                v = float(low.split()[-1])
                self.cfg["min_acc"] = max(0.0, min(100.0, v))
                _save_cfg(self.cfg)
                await reply(f"OK: min_acc={self.cfg['min_acc']:.1f}%")
            except Exception:
                await reply("Format: `curriculum set min_acc 95` (persen)")
            return

        if low.startswith("curriculum set hhmm"):
            try:
                arg = content.split()[-1]
                t = _parse_hhmm(arg)
                self.cfg["report_hhmm"] = f"{t.hour:02d}{t.minute:02d}"
                _save_cfg(self.cfg)
                await reply(f"OK: report HHMM={self.cfg['report_hhmm']}")
            except Exception:
                await reply("Format: `curriculum set hhmm 2355`")
            return

        if low.startswith("curriculum set tz"):
            try:
                arg = content.split()[-1]
                if arg.startswith(("+", "-")) and len(arg.replace(":", "")) in (3, 4):
                    a = arg.replace(":", "").lstrip("+")
                    sign = -1 if arg.startswith("-") else 1
                    if len(a) == 3:
                        h, m = int(a[0]), int(a[1:])
                    else:
                        h, m = int(a[:2]), int(a[2:])
                    minutes = sign * (h*60 + m)
                else:
                    minutes = int(arg)  # langsung dalam menit
                self.cfg["tz_offset_minutes"] = int(minutes)
                _save_cfg(self.cfg)
                await reply(f"OK: tz_offset_minutes={self.cfg['tz_offset_minutes']}")
            except Exception:
                await reply("Format: `curriculum set tz +0700` atau `curriculum set tz 420` (menit)")
            return

        if low.startswith("curriculum set channel"):
            try:
                arg = content.split(maxsplit=3)[-1].strip()
                cid: Optional[int] = None
                if arg.startswith("#"):
                    # nama channel
                    name = arg[1:].lower()
                    for g in self.bot.guilds:
                        for ch in getattr(g, "text_channels", []):
                            if (getattr(ch, "name", "") or "").lower() == name:
                                cid = int(ch.id); break
                        if cid: break
                else:
                    cid = int(arg)
                if cid:
                    self.cfg["report_channel_id"] = cid
                    _save_cfg(self.cfg)
                    await reply(f"OK: report_channel_id={cid}")
                else:
                    await reply("Channel tidak ditemukan. Pakai: `curriculum set channel 1234567890` atau `curriculum set channel #log-botphising`")
            except Exception:
                await reply("Format: `curriculum set channel <id | #name>`")
            return

        if low == "curriculum report now":
            try:
                obj = json.loads(PROGRESS_FILE.read_text(encoding="utf-8")) if PROGRESS_FILE.exists() else {"xp_total": 0}
            except Exception:
                obj = {"xp_total": 0}
            # gunakan bridge runtime agar report real-time
            xp_run = _probe_total_xp_runtime(self.bot)
            xp = int(obj.get("xp_total", 0))
            if xp_run is not None:
                xp = max(xp, int(xp_run))
            target = max(1, int(self.cfg.get("target_xp", 2000)))
            pct = int(min(100, round((xp / target) * 100)))
            acc = _probe_accuracy()
            tz = int(self.cfg.get("tz_offset_minutes", 420))
            try:
                d0 = dt.datetime.strptime(obj.get("created_at", _now_local(tz).strftime("%Y-%m-%d")), "%Y-%m-%d").date()
            except Exception:
                d0 = _now_local(tz).date()
            days = max(0, (_now_local(tz).date() - d0).days)
            ch = self._report_channel()
            if ch:
                await ch.send(f"**Curriculum TK→SD (manual)** — XP {xp} ({pct}%), Days {days}/{self.cfg.get('min_days',7)}, Acc7d {'N/A' if acc is None else f'{acc:.1f}%'} (min {self.cfg.get('min_acc',95.0)}%)")
                await reply("OK: dikirim ke channel report.")
            else:
                await reply("Channel report belum diset. Gunakan: `curriculum set channel <id | #name>`")
            return

        if low == "curriculum enable":
            self.cfg["enabled"] = True
            _save_cfg(self.cfg)
            await reply("OK: enabled=True")
            return

        if low == "curriculum disable":
            self.cfg["enabled"] = False
            _save_cfg(self.cfg)
            await reply("OK: enabled=False")
            return

async def setup(bot):
    await bot.add_cog(CurriculumTKSD(bot))