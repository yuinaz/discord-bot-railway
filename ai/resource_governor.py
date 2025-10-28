"""Legacy shim — canonical implementation moved to `satpambot.ai.resource_governor`.

Importing `ai.resource_governor` will re-export symbols from
`satpambot.ai.resource_governor` and emit a DeprecationWarning to guide
developers to the new package path.
"""
from __future__ import annotations
import warnings
warnings.warn("Importing 'ai.resource_governor' is deprecated; use 'satpambot.ai.resource_governor' instead", DeprecationWarning)
from satpambot.ai.resource_governor import *  # type: ignore
