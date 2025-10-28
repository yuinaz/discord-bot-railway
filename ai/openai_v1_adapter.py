"""Legacy shim — canonical implementation moved to `satpambot.ai.openai_v1_adapter`.

This module re-exports the new location and emits a DeprecationWarning.
"""
from __future__ import annotations
import warnings
warnings.warn("Importing 'ai.openai_v1_adapter' is deprecated; use 'satpambot.ai.openai_v1_adapter' instead", DeprecationWarning)
from satpambot.ai.openai_v1_adapter import *  # type: ignore
