Patch: scripts/smoke_utils.py for offline smoke harness
-------------------------------------------------------
This adds a local 'scripts/smoke_utils.py' so that 'python scripts/smoke_deep.py'
imports the project copy (instead of any 3rd-party module on site-packages).

Provided DummyBot implements:
  - wait_until_ready() [async no-op]
  - add_cog() [async-friendly]
  - get_all_channels(), get_channel()
  - get_user(), fetch_user() [async]
  - add_check(), get_guild()
  - _DummyBot alias

Install:
  1) Unzip into the ROOT of your repo (where 'scripts/' lives).
  2) Run:  python patches/verify_snippet.py   (optional)
  3) Run:  export PYTHONPATH="$(pwd)"
           python scripts/smoke_deep.py

No config formats are modified by this patch.
