"""Minimal stub for dashboard.webui to satisfy lint/compile.
Provides a dummy Blueprint-like object so imports won't fail during lint.
"""
from __future__ import annotations

try:
    from flask import Blueprint  # type: ignore
    bp = Blueprint("dashboard_stub", __name__)
except Exception:  # pragma: no cover
    class _DummyBP:
        def get(self, *a, **k):
            def deco(f):
                return f
            return deco
        def post(self, *a, **k):
            def deco(f):
                return f
            return deco
    bp = _DummyBP()

# Representative endpoint stubs (no runtime effect if not registered)
@bp.get("/dashboard/health")
def dashboard_health():  # pragma: no cover
    return {"ok": True}
