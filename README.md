
# SatpamBot — Discord Security Bot + Dashboard

SatpamBot is a Discord moderation/security bot with a minimal web dashboard. It focuses on **anti‑phishing**, **link/attachment heuristics**, **image phash detection**, and quality‑of‑life tools for moderators.  
This repo also includes a **Dashboard** (theme: `gtake`) with a mini monitor and security views.

> **This README is tailored to your current setup** (Render deploy + GitHub auto‑sync for WL/BL). Adjust paths/names to your environment where needed.

---

## ✨ Highlights

- **Anti‑Phishing Link Guard**: domain allow/deny, risky TLD thresholds, punycode flag, URL resolve, per‑user rate limits.
- **Image Scam Detection**: pHash/aHash/dHash + optional ORB matches, auto‑ban thresholds.
- **Whitelist/Blacklist via Threads** (no commands needed):  
  In `#log-botphising` create 2 threads: any thread **containing** `whitelist` and another **containing** `blacklist`.  
  Moderators can just type `domain.com` or upload `.txt/.json` to update lists.
- **Memory Thread ("memory W*B")**: pinned embed + attachments `whitelist.txt` and `blacklist.txt`, updated automatically.
- **GitHub Sync (optional)**: persist WL/BL changes by committing JSON/TXT files back to the repo (anti‑reset across redeploys).
- **Does not modify** your existing `ban` / `testban` commands or the web UI.

---

## 🧱 Architecture (high‑level)

```
satpambot/
  bot/
    modules/discord_bot/
      cogs/
        auto_lists.py         # NEW: watch WL/BL threads, save domains, update "memory W*B"
        ... (other cogs)
      helpers/
        lists_loader.py       # NEW compat: unified load/save for WL/BL
        memory_wb.py          # NEW: create/update the "memory W*B" thread (embed + files)
        github_sync.py        # NEW: commit files to GitHub via REST API
  dashboard/
    ... (web UI; untouched by this patch)
data/
  whitelist_domains.json      # list[str]
  blacklist_domains.json      # list[str]
  url_whitelist.json          # {"allow": [...]}
  url_blocklist.json          # {"domains": [...]}
whitelist.txt                 # mirror (1 domain/line)
blacklist.txt
scripts/
  migrate_lists.py            # normalize old formats -> unified files above
  cleanup_duplicates.py       # remove common duplicate folders (optional)
```

> Your bot’s cog loader auto‑scans `cogs/`, so `auto_lists.py` is loaded without further changes.

---

## 🔐 Discord Setup

1. In the Discord Developer Portal, **enable _Message Content Intent_**.
2. Invite the bot with permissions to your server.
3. In your server, ensure the bot has at least:
   - `Send Messages`, `Read Message History`
   - `Create/Manage Threads`
   - `Attach Files`, `Add Reactions`
   - *(Optional)* `Manage Messages` (to clean up old attachment messages in the memory thread)

---

## ⚙️ Environment Variables

> Below are the **relevant** variables for this patch. Keep your existing ones for other features (OCR, NSFW, etc.).  
> **Never commit real secrets.** Set them in Render or your host’s secret store.

**Log & Memory Thread**
- `LOG_CHANNEL_ID` — numeric ID of `#log-botphising` (preferred)
- `LOG_CHANNEL_NAME` — fallback name (default `log-botphising`)
- `MEMORY_WB_THREAD_NAME` — thread name for embed/files (default `memory W*B`)

**GitHub Sync (optional but recommended)**
- `AUTO_LISTS_GH_SYNC=1` — enable commit of WL/BL files back to this repo
- `GITHUB_TOKEN` — GitHub PAT with `repo` scope
- `GITHUB_REPO` — e.g. `yuinaz/discord-bot-railway`
- `GITHUB_BRANCH` — e.g. `main`

**Repo paths for WL/BL (override if you prefer paths in repo)**
- `GITHUB_WHITELIST_JSON_PATH` — default `data/whitelist_domains.json` *(you customised to `satpambot/data/whitelist.json`)*
- `GITHUB_BLACKLIST_JSON_PATH` — default `data/blacklist_domains.json` *(you customised to `satpambot/data/blacklist.json`)*
- `GITHUB_URL_WL_JSON_PATH` — default `data/url_whitelist.json`
- `GITHUB_URL_BL_JSON_PATH` — default `data/url_blocklist.json`
- `GITHUB_WHITELIST_TXT_PATH` — default `whitelist.txt`
- `GITHUB_BLACKLIST_TXT_PATH` — default `blacklist.txt`

**Local file paths (used by the engine)**
- `WHITELIST_DOMAINS_FILE` — default `data/whitelist_domains.json`
- `BLACKLIST_DOMAINS_FILE` — default `data/blacklist_domains.json`
- `URL_WHITELIST_JSON_FILE` — default `data/url_whitelist.json`
- `URL_BLOCKLIST_JSON_FILE` — default `data/url_blocklist.json`

> Tip: Avoid setting `PYTHONPATH` to invalid values. If present as `PYTHONPATH="="`, remove it.

---

## 🚀 Local Development

```bash
# (first time) unify legacy list files -> standard
python scripts/migrate_lists.py

# run your app (example; adjust to your entrypoint)
python main.py
# or: uvicorn/gunicorn for the web, and a worker for the bot (depending on your setup)
```

**What to expect on startup**
- Loader logs that `auto_lists` is loaded.
- Bot ensures/creates the thread **“memory W*B”** under `#log-botphising`.
- A pinned embed appears with counts (WL/BL), plus a message with attachments `whitelist.txt` and `blacklist.txt`.
- If `AUTO_LISTS_GH_SYNC=1`, WL/BL edits create commits in your GitHub repo.

---

## 🧪 Moderator Flow (No Commands)

- In the **whitelist thread** (name contains `whitelist`), type:  
  `pixiv.com` → ✅ saved to WL files + memory thread updated.
- In the **blacklist thread** (name contains `blacklist`), type:  
  `contoh-phish.com` → ✅ saved to BL files + memory thread updated.
- Upload `.txt` (1 domain per line) or `.json` (list or `{allow:[]}/{domains:[]}`) to bulk update.

Files updated by each change:
- `data/whitelist_domains.json`
- `data/blacklist_domains.json`
- `data/url_whitelist.json`
- `data/url_blocklist.json`
- `whitelist.txt` / `blacklist.txt`

(If GitHub sync is enabled, these are also committed to the repo on each change.)

---

## ☁️ Deploy to Render

> Assumes a single service that runs both web + bot (your `MODE=both`).

1. Add the environment variables above in Render.
2. Ensure secrets are set (Discord token, OCR keys, etc.).
3. Set your **Start Command** to your entrypoint, e.g.:  
   `python main.py`
4. Deploy.

**Sanity checks on Render logs**
- No `AttributeError` from `helpers.lists_loader`.
- Lines indicating `auto_lists` loaded and the memory thread updated.
- If `AUTO_LISTS_GH_SYNC=1`, look for the “update WL()/BL()” commit messages in GitHub.

---

## 🔒 Security Notes

- **Do not paste real tokens/keys into issues or public README.** Use environment variables.
- If a secret was exposed, **rotate it immediately** (GitHub PAT, OpenAI key, Google Safe Browsing, OCR key, metrics token, Flask secret key, etc.).
- Limit bot permissions to what’s necessary.

---

## 📜 License

Choose a license and place it as `LICENSE` in the repo (MIT/Apache-2.0/etc.).

---

## 🙌 Credits

Thanks to the maintainers & contributors. Dashboard theme preset: `gtake`.  
This README was generated to match your current configuration (Render + GitHub WL/BL sync).
