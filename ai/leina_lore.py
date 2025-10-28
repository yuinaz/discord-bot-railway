"""Legacy shim — canonical implementation moved to `satpambot.ai.leina_lore`.

This module re-exports the implementation from `satpambot.ai.leina_lore` and
emits a DeprecationWarning to encourage using the package path under
`satpambot.ai`.
"""
from __future__ import annotations
import warnings
warnings.warn("Importing 'ai.leina_lore' is deprecated; use 'satpambot.ai.leina_lore' instead", DeprecationWarning)
from satpambot.ai.leina_lore import *  # type: ignore