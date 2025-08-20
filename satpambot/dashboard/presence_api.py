
from __future__ import annotations
from flask import Blueprint, jsonify, request
from .presence_store import read_presence, write_presence

bp = Blueprint("presence_api", __name__)

@bp.get("/api/presence")
def api_get_presence():
    return jsonify(read_presence())

@bp.post("/api/presence")
def api_set_presence():
    data = request.get_json(force=True, silent=True) or {}
    write_presence(data)
    return jsonify({"ok": True})
