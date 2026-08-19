"""FinanceCalc - Calculadora Financiera TVM moderna.

Backend Flask: toda la matematica financiera vive en tvm.py (Python puro,
sin dependencias externas de calculo). El frontend es HTML/CSS/JS y consume
esta API via fetch.
"""

from flask import Flask, jsonify, render_template, request

from tvm import FREQ_LABELS, TVMError, amortization_schedule, calculate

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html", freq_labels=FREQ_LABELS)


@app.route("/api/solve", methods=["POST"])
def api_solve():
    data = request.get_json(force=True, silent=True) or {}
    try:
        result = calculate(data)
        return jsonify({"ok": True, "result": result})
    except TVMError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "Datos invalidos. Revisa los numeros ingresados."}), 400
    except OverflowError:
        return jsonify({"ok": False, "error": "El resultado es demasiado grande. Revisa los parametros."}), 400


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


if __name__ == "__main__":
    app.run(debug=True, port=5000)
