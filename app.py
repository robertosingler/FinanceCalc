"""FinanceCalc - Calculadora Financiera TVM moderna.

Backend Flask: la matematica financiera vive en tvm.py. Autenticacion via
Google OAuth (auth.py), datos persistidos en SQLite (models.py). El
frontend de la calculadora es HTML/CSS/JS y consume esta API via fetch.
"""

import os

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, session

load_dotenv()

from auth import auth_bp, current_user, init_oauth, login_required  # noqa: E402
from models import CalculationHistory, SavedScenario, User, db  # noqa: E402
from tvm import FREQ_LABELS, TVMError, amortization_schedule, calculate  # noqa: E402

app = Flask(__name__, instance_relative_config=True)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me-in-.env")

os.makedirs(app.instance_path, exist_ok=True)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(app.instance_path, "financecalc.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["GOOGLE_CLIENT_ID"] = os.environ.get("GOOGLE_CLIENT_ID", "")
app.config["GOOGLE_CLIENT_SECRET"] = os.environ.get("GOOGLE_CLIENT_SECRET", "")

db.init_app(app)
init_oauth(app)
app.register_blueprint(auth_bp)

ADMIN_EMAILS = {e.strip().lower() for e in os.environ.get("ADMIN_EMAILS", "").split(",") if e.strip()}

with app.app_context():
    db.create_all()


# ---------------------------------------------------------------- Paginas --

@app.route("/")
def landing():
    return render_template("landing.html", user=current_user())


@app.route("/app")
def calculator():
    user = current_user()
    return render_template("index.html", freq_labels=FREQ_LABELS, user=user)


@app.route("/terms")
def terms():
    return render_template("terms.html")


@app.route("/privacy")
def privacy():
    return render_template("privacy.html")


@app.route("/admin/users")
@login_required
def admin_users():
    user = current_user()
    if not ADMIN_EMAILS or user.email.lower() not in ADMIN_EMAILS:
        return render_template("error.html", code=403,
                                message="No tenes permiso para ver esta pagina."), 403
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template("admin_users.html", users=users)


# -------------------------------------------------------------------- API --

@app.route("/api/me")
def api_me():
    user = current_user()
    return jsonify({"ok": True, "user": user.to_dict() if user else None})


@app.route("/api/solve", methods=["POST"])
def api_solve():
    data = request.get_json(force=True, silent=True) or {}
    try:
        result = calculate(data)
    except TVMError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "Datos invalidos. Revisa los numeros ingresados."}), 400
    except OverflowError:
        return jsonify({"ok": False, "error": "El resultado es demasiado grande. Revisa los parametros."}), 400

    user = current_user()
    if user:
        solved_field = data.get("solve_for")
        merged = {**data, solved_field: result.get(solved_field)}
        entry = CalculationHistory(
            user_id=user.id,
            solved_field=solved_field,
            pv=merged.get("pv"), pmt=merged.get("pmt"), fv=merged.get("fv"),
            rate=merged.get("rate"), n=merged.get("n"),
            freq=merged.get("freq"), rate_type=merged.get("rate_type"),
            mode=merged.get("mode"), decimals=merged.get("decimals"),
            periodic_rate_pct=result.get("periodic_rate_pct"),
        )
        db.session.add(entry)
        db.session.commit()

    return jsonify({"ok": True, "result": result})


@app.route("/api/amortization", methods=["POST"])
def api_amortization():
    data = request.get_json(force=True, silent=True) or {}
    try:
        from tvm import periodic_rate

        freq = int(data.get("freq", 12))
        rate_type = data.get("rate_type", "effective")
        mode = data.get("mode", "end")
        type_ = 1 if mode == "begin" else 0
        decimals = int(data.get("decimals", 2))

        pv = float(data["pv"])
        pmt = float(data["pmt"])
        rate = float(data["rate"])
        n = data["n"]

        i = periodic_rate(rate, freq, rate_type)
        schedule = amortization_schedule(pv, pmt, i, int(round(float(n))), type_, decimals)

        total_interest = round(sum(row["interest"] for row in schedule), decimals)
        total_paid = round(sum(row["payment"] for row in schedule), decimals)

        return jsonify({
            "ok": True,
            "schedule": schedule,
            "summary": {
                "total_interest": total_interest,
                "total_paid": total_paid,
                "final_balance": schedule[-1]["balance"] if schedule else 0,
            },
        })
    except KeyError as e:
        return jsonify({"ok": False, "error": f"Falta el campo {e}"}), 400
    except TVMError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "Datos invalidos para generar la amortizacion."}), 400


@app.route("/api/history", methods=["GET"])
@login_required
def api_history_list():
    user = current_user()
    rows = CalculationHistory.query.filter_by(user_id=user.id) \
        .order_by(CalculationHistory.created_at.desc()).limit(50).all()
    return jsonify({"ok": True, "history": [r.to_dict() for r in rows]})


@app.route("/api/history/<int:entry_id>", methods=["DELETE"])
@login_required
def api_history_delete(entry_id):
    user = current_user()
    row = CalculationHistory.query.filter_by(id=entry_id, user_id=user.id).first()
    if not row:
        return jsonify({"ok": False, "error": "No encontrado"}), 404
    db.session.delete(row)
    db.session.commit()
    return jsonify({"ok": True})


@app.route("/api/saved", methods=["GET"])
@login_required
def api_saved_list():
    user = current_user()
    rows = SavedScenario.query.filter_by(user_id=user.id) \
        .order_by(SavedScenario.created_at.desc()).all()
    return jsonify({"ok": True, "saved": [r.to_dict() for r in rows]})


@app.route("/api/saved", methods=["POST"])
@login_required
def api_saved_create():
    user = current_user()
    data = request.get_json(force=True, silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"ok": False, "error": "El escenario necesita un nombre"}), 400

    row = SavedScenario(
        user_id=user.id, name=name,
        pv=data.get("pv"), pmt=data.get("pmt"), fv=data.get("fv"),
        rate=data.get("rate"), n=data.get("n"), freq=data.get("freq"),
        rate_type=data.get("rate_type"), mode=data.get("mode"),
        decimals=data.get("decimals"),
    )
    db.session.add(row)
    db.session.commit()
    return jsonify({"ok": True, "saved": row.to_dict()})


@app.route("/api/saved/<int:entry_id>", methods=["DELETE"])
@login_required
def api_saved_delete(entry_id):
    user = current_user()
    row = SavedScenario.query.filter_by(id=entry_id, user_id=user.id).first()
    if not row:
        return jsonify({"ok": False, "error": "No encontrado"}), 404
    db.session.delete(row)
    db.session.commit()
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
