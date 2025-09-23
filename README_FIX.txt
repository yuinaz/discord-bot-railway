Fix: no dependency on bot.loop in __init__ (tasks start on on_ready)
-------------------------------------------------------------------
- Menghindari AttributeError: DummyBot has no attribute 'loop' saat smoke test.
- Sweeper & backfill tetap ada; task dibuat via asyncio.create_task() pada on_ready().
- Tidak mengubah ENV.

Cara pasang:
1) Replace file cogs/auto_role_anywhere.py ini di repo kamu (dan config JSON kalau perlu).
2) Jalankan smoke: python scripts/smoke_cogs.py -> harus OK.
3) Deploy / restart bot.

