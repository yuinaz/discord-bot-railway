from flask import Blueprint, request, redirect, session, render_template_string, current_app as app
import datetime
import os

editor_bp = Blueprint("editor", __name__)

@editor_bp.route("/editor", methods=["GET", "POST"])
def editor():
    if not session.get("admin"):
        return redirect("/login")

    filepath = "main.py"
    
    if request.method == "POST":
        new_code = request.form.get("code")
        confirm = request.form.get("confirm")
        if not confirm:
            return "❌ Perlu konfirmasi sebelum menyimpan", 400

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(new_code)
            with open("editor_log.txt", "a", encoding="utf-8") as log:
                log.write(f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] main.py diedit dari dashboard\n")
        except Exception as e:
            return f"❌ Gagal menyimpan file: {e}", 500

        return redirect("/dashboard")

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            current_code = f.read()
    except Exception as e:
        current_code = f"# Gagal membuka file: {e}"

    return render_template_string("""
    <h2>Edit main.py</h2>
    <form method='POST'>
      <textarea name='code' rows='25' style='width:100%'>{{ current_code }}</textarea><br>
      <label><input type='checkbox' name='confirm' required> Saya yakin ingin menyimpan perubahan</label><br>
      <button type='submit'>💾 Simpan</button>
    </form>
    """, current_code=current_code)
