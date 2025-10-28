"""Legacy shim — canonical implementation moved to `satpambot.ai.gemini_client`.

Importing `ai.gemini_client` re-exports from `satpambot.ai.gemini_client` and emits a
DeprecationWarning to guide developers to the new package path.
"""
from __future__ import annotations
import warnings
warnings.warn("Importing 'ai.gemini_client' is deprecated; use 'satpambot.ai.gemini_client' instead", DeprecationWarning)
from satpambot.ai.gemini_client import *  # type: ignore
