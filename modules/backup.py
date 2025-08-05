from flask import Blueprint, jsonify
import datetime

backup_bp = Blueprint("backup", __name__)

@backup_bp.route("/backup")
def backup():
    return jsonify({
        "message": "📦 Backup route is active",
        "timestamp": datetime.datetime.now().isoformat()
    })