# === add-only: security reorder endpoint ===
try:
    from flask import request, jsonify
    from pathlib import Path as _P
    import json as _json

    __SEC_FILE = _P("data") / "security_order.json"
    def __register_security_api(app):
        if not app.view_functions.get("api_security_reorder"):
            @app.post("/api/security/reorder")
            def api_security_reorder():
                payload = request.get_json(force=True, silent=True) or {}
                try:
                    __SEC_FILE.parent.mkdir(parents=True, exist_ok=True)
                    __SEC_FILE.write_text(_json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
                    return jsonify({"ok": True, "saved": True})
                except Exception as e:
                    return jsonify({"ok": False, "error": str(e)}), 500
    if 'register_webui_builtin' in globals():
        _old = register_webui_builtin
        def register_webui_builtin(app):
            _old(app)
            try:
                __register_security_api(app)
            except Exception:
                pass
    else:
        def register_webui_builtin(app):
            try:
                __register_security_api(app)
            except Exception:
                pass
except Exception:
    pass
