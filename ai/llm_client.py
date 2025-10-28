"""Legacy shim — canonical implementation moved to `satpambot.ai.llm_client`.

This module re-exports the public API from `satpambot.ai.llm_client` and
emits a DeprecationWarning to encourage using the new import path.
"""
from __future__ import annotations
import warnings
warnings.warn("Importing 'ai.llm_client' is deprecated; use 'satpambot.ai.llm_client' instead", DeprecationWarning)
from satpambot.ai.llm_client import *  # type: ignore
