# 🛡️ SatpamBot – Discord Security Bot + Dashboard + Desktop Widget
(README ringkas — versi lengkap tersedia di INSTALLATION.txt)

Fitur: URL Guard + VirusTotal, OCR + blockwords editor, image hash blacklist, image classifier no-text, autoban NSFW, whitelist channel/role, logging embed+sticker+ban-log upsert, live stats; dashboard tema & security; widget web + Windows notifier; desktop widget (Electron) dengan tray, restart, auto-update & HMAC.

## Quick Start
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
ENV_PROFILE=local python main.py
```
- Dashboard: http://localhost:8080/dashboard
- Desktop widget: `cd desktop-widget && npm install && npm start`

Lihat **INSTALLATION.txt** untuk langkah detail, ENV lengkap, build installer Windows, dan auto-update.


### Ban Log Channels (optional)
- `BAN_LOG_CHANNEL_ID` untuk embed detail ban.
- `MOD_COMMAND_CHANNEL_ID` akan menyimpan 1 embed ban-list yang di-update (upsert).
