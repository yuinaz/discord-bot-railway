# Live Config (Render Free + MiniPC)

Ubah setting bot **tanpa commit**. Backend: **file**, **url (Gist)**, **discord_message**, **discord_topic**.

## ENV
- `LIVE_CONFIG_SOURCE` = file | url | discord_message | discord_topic (default: file)
- `LIVE_CONFIG_PATH` (untuk file) default: `satpambot_config.live.json`
- `LIVE_CONFIG_URL` (untuk url)
- `LIVE_CONFIG_DISCORD_CHANNEL_ID` (untuk discord_*)
- `LIVE_CONFIG_DISCORD_MESSAGE_ID` (untuk discord_message)
- `LIVE_CONFIG_POLL_INTERVAL` (detik) default: 4 (file/discord), 10 (url)
- `RUNTIME_FLAGS_PATH` default: `data/runtime_flags.json`

## Contoh JSON
```json
{
  "dm_muzzle_mode": "log",
  "selfheal": true,
  "selfheal_quiet": true,
  "selfheal_thread_disable": true,
  "automaton": true,
  "automaton_quiet": true,
  "automaton_thread_disable": true,
  "log_channel_id": "1400375184048787566",
  "selfheal_thread_channel_id": "",
  "automaton_thread_channel_id": ""
}
```

Perintah admin: `!livecfg` (status / apply / source)