
# Deep Smoke Test

This adds a **deeper** offline check, beyond `scripts/smoke_cogs.py`:

- Imports every cog
- Calls `setup(bot)` **twice** and verifies **idempotency**
- Captures logs during setup to find **duplicate/noisy** messages
- Counts background tasks scheduled via `bot.loop.create_task`
- Lists **ENV keys** referenced in code (via `os.getenv`) and whether they are set

## Run

```bash
python scripts/smoke_deep.py
# or strict mode (turns WARN into non-zero exit)
python scripts/smoke_deep.py --strict
```

No token required. Works on Render free plan and on MINIPC.
