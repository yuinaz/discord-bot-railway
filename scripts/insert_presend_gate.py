from __future__ import annotations

# scripts/insert_presend_gate.py
"""
Robust injector for a pre-send PublicChatGate guard inside ChatNeuroLite.on_message.

Run with:
    python -m scripts.insert_presend_gate

If it can't find the handler, it will print helpful hints without changing files.
"""
from pathlib import Path
import re, sys

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "satpambot" / "bot" / "modules" / "discord_bot" / "cogs" / "chat_neurolite.py"

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

def main():
    if not TARGET.exists():
        print(f"[ERROR] Cannot find: {TARGET}")
        print("Tip: ensure you're running from project root (where 'satpambot/' lives).")
        sys.exit(2)

    src = TARGET.read_text(encoding="utf-8")
    if "PublicChatGate pre-send guard (auto-injected)" in src:
        print("[OK] Guard already present. Nothing to do.")
        return

    # Try to locate ChatNeuroLite.on_message definition (decorator optional)
    # Capture indentation to respect file style.
    pat = re.compile(
        r'^(?P<indent>[ \t]*)async\s+def\s+(?P<name>on_message|_on_message)\s*\(\s*self\s*,\s*message\s*(?::[^\)]*)?\)\s*:\s*$',
        re.M
    )
    m = pat.search(src)
    if not m:
        print("[ERROR] Could not locate an on_message(self, message) handler in chat_neurolite.py")
        print("Hints:")
        print("- Make sure ChatNeuroLite uses an on_message listener; if it uses a different method, tell me its name.")
        print("- Or paste the first ~80 lines of chat_neurolite.py here so I can tailor the injector.")
        sys.exit(3)

    indent = m.group("indent") + "    "  # one level deeper than def
    insert_pos = m.end()
    guard = GUARD_TMPL.format(indent=indent)
    new_src = src[:insert_pos] + "\n" + guard + src[insert_pos:]
    TARGET.write_text(new_src, encoding="utf-8")
    print(f"[OK] Injected pre-send guard into {TARGET}")
    print(f"[INFO] Handler function: {m.group('name')} at byte {insert_pos}")

if __name__ == "__main__":
    main()
