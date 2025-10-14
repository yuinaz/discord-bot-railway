SatpamLeina — Full Patch Bundle v1

Isi:
• phish_watcher.py
• imagephish_ref_indexer_v2.py
• local_all.json
• local_patch_phish_v3.json
• local_patch_thread_index.json
• local_patch_status_and_clearchat.json
• verify_after_merge.py
• merge_cmd.txt

Langkah cepat:
1) Ekstrak folder 'bundle' ke root repo (selevel 'scripts' dan 'satpambot').
2) Merge config:  python -m scripts.merge_local_json bundle/local_all.json
3) Salin cogs:
     cp bundle/phish_watcher.py satpambot/bot/modules/discord_bot/cogs/phish_watcher.py
     cp bundle/imagephish_ref_indexer_v2.py satpambot/bot/modules/discord_bot/cogs/imagephish_ref_indexer_v2.py
4) Restart bot.
