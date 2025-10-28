"""Legacy shim — canonical implementation moved to `satpambot.ai.leina_personality`.

Importing this module will re-export from `satpambot.ai.leina_personality` and
emit a DeprecationWarning so callers migrate to the new package path.
"""
from __future__ import annotations
import warnings
warnings.warn("Importing 'ai.leina_personality' is deprecated; use 'satpambot.ai.leina_personality' instead", DeprecationWarning)
from satpambot.ai.leina_personality import *  # type: ignore