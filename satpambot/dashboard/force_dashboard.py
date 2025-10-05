"""Minimal stub for force_dashboard to satisfy lint/compile.
This module is optional and not required for Render free plan deployment.
"""
from __future__ import annotations


# No-op helpers (avoid import-time side effects)
def mount_force_dashboard(app) -> None:  # pragma: no cover
    """Optional: attach dashboard routes if needed."""
    try:
        app  # just to avoid unused
    except Exception:
        pass
