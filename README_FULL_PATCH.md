# SatpamBot — Full Auto‑Update + OpenAI v1 Hotfix (Flat Patch)

**Tidak mengubah Render config-mu:**
- Build: `bash scripts/build_render.sh`
- Start: `python main.py`
- Pre‑Deploy: (kosong)

## Yang disediakan
- **Auto Update Manager (cog)** dengan owner‑gating untuk modul krusial (ban/moderation/anti‑image*).
- **Updater PIP non‑kritis** (MiniPC) + rollback otomatis kalau smoketest gagal.
- **Render‑aware**: di Render, updater hanya laporan (runtime FS ephemeral).
- **Hotfix OpenAI v1**: adapter + `scripts/apply_hotfixes.py` untuk migrasi call‑sites lama.
- **ENV melekat** via `sitecustomize.py` (load `.env` jika ada; default aman jika kosong).
- **neuro_lite.toml** default aman (mention‑only, no DM).

## Slash Commands
- `/update_check` – cek paket outdated
- `/update_apply` – update paket non‑kritis (MiniPC)
- `/update_approve package:<nama|all>` – owner/admin approve
- `/update_schedule days:<n>` – atur interval (default 4 hari)

## Cara pakai
1) Salin semua file patch ini ke **root repo** (flat).
2) Push. Render tidak perlu ubah Build/Start Command.
3) (Opsional MiniPC) Salin ENV dari Render → `.env` berdasarkan `.env.sample`.

Rollback: hapus file‑file patch ini.
