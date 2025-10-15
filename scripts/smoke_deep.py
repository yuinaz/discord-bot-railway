
import os, sys
from pathlib import Path
_HERE = Path(__file__).resolve()
_ROOT = _HERE.parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "scripts"))
os.environ.setdefault("SMOKE_MODE","1")

from scripts.smoke_utils import DummyBot, retrofit
from satpambot.ml.neuro_lite_memory_fix import bump_progress, load_junior
from satpambot.bot.utils.embed_scribe import EmbedScribe
from satpambot.bot.utils.dupe_guard import DuplicateSuppressor

bot = retrofit(DummyBot())

bump_progress("TK", "L1", 0.1)
j = load_junior()
assert "overall" in j

scribe = EmbedScribe(bot)
dedupe = DuplicateSuppressor()

print("[OK] smoke_deep baseline complete")
