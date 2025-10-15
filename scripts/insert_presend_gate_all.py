from __future__ import annotations

# scripts/insert_presend_gate_all.py
"""
Inject a pre-send PublicChatGate guard into *all* on_message listeners across cogs.

Run:
    python -m scripts.insert_presend_gate_all

What it does:
- Scans satpambot/bot/modules/discord_bot/cogs/*.py
- For each file, finds any `async def on_message(self, message: discord.Message):` (or _on_message)
- Inserts a guard block right after the function signature (idempotent).

Guard uses `self.bot.get_cog("PublicChatGate")` to decide whether to early-return.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
COGS_DIR = ROOT / "satpambot" / "bot" / "modules" / "discord_bot" / "cogs"

GUARD_TMPL = """{indent}# --- PublicChatGate pre-send guard (auto-injected) ---
{indent}gate = None
{indent}try:
{indent}    gate = self.bot.get_cog("PublicChatGate")
{indent}except Exception:
{indent}    pass
{indent}try:
{indent}    if message.guild and gate and hasattr(gate, "should_allow_public_reply") and not gate.should_allow_public_reply(message):
{indent}        return
{indent}except Exception:
{indent}    pass
{indent}# --- end guard ---
"""

PAT = re.compile(
    r'^(?P<indent>[ \t]*)async\s+def\s+(?P<name>on_message|_on_message)\s*\(\s*self\s*,\s*message\s*(?::[^\)]*)?\)\s*:\s*$',
    re.M
)

def process_file(path: Path) -> bool:
    src = path.read_text(encoding="utf-8")
    if "PublicChatGate pre-send guard (auto-injected)" in src:
        return False
    m = PAT.search(src)
    if not m:
        return False
    indent = m.group("indent") + "    "
    insert_pos = m.end()
    guard = GUARD_TMPL.format(indent=indent)
    new_src = src[:insert_pos] + "\n" + guard + src[insert_pos:]
    path.write_text(new_src, encoding="utf-8")
    return True

def main():
    if not COGS_DIR.exists():
        print("[ERROR] Cogs directory not found:", COGS_DIR)
        return
    changed = 0
    for p in sorted(COGS_DIR.glob("*.py")):
        try:
            if process_file(p):
                print("[OK] Injected guard into", p)
                changed += 1
        except Exception as e:
            print("[WARN] Skipped", p, "->", e)
    print("[DONE] Files changed:", changed)

if __name__ == "__main__":
    main()
