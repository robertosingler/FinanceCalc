"""Autenticacion via Google OAuth (Authlib). No se manejan contrasenas: la
identidad viene siempre de Google, y el registro solo completa telefono +
consentimientos (terminos y marketing por email)."""

import traceback
from datetime import datetime
from functools import wraps

from authlib.integrations.flask_client import OAuth
from flask import (Blueprint, current_app, jsonify, redirect, render_template,
                    request, session, url_for)

from models import User, db

oauth = OAuth()
auth_bp = Blueprint("auth", __name__)


def init_oauth(app):
    oauth.init_app(app)
    oauth.register(
        name="google",
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )


def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    return User.query.get(uid)


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            if request.path.startswith("/api/"):
                return jsonify({"ok": False, "error": "No autenticado. Inicia sesion para usar esta funcion."}), 401
            return redirect("/")
        return f(*args, **kwargs)
    return wrapper


@auth_bp.route("/login/google")
def login_google():
    try:
        redirect_uri = url_for("auth.google_callback", _external=True)
        return oauth.google.authorize_redirect(redirect_uri)
    except Exception as e:
        current_app.logger.error("Error en /login/google:\n" + traceback.format_exc())
        return (f"<pre>Error al iniciar el login con Google:\n\n"
                f"{type(e).__name__}: {e}\n\n{traceback.format_exc()}</pre>"), 500


@auth_bp.route("/login/google/callback")
def google_callback():
    try:
        token = oauth.google.authorize_access_token()
        profile = token.get("userinfo") or oauth.google.parse_id_token(token)

        google_id = profile["sub"]
        email = profile["email"]

        user = User.query.filter_by(google_id=google_id).first()

        if user:
            user.last_login_at = datetime.utcnow()
            user.name = profile.get("name") or user.name
            user.avatar_url = profile.get("picture") or user.avatar_url
            db.session.commit()
            session["user_id"] = user.id
            return redirect("/app")

        # Usuario nuevo: falta telefono + aceptar terminos -> completar registro
        session["pending_oauth"] = {
            "google_id": google_id,
            "email": email,
            "name": profile.get("name", ""),
            "avatar_url": profile.get("picture", ""),
        }
        return redirect(url_for("auth.complete_registration"))
    except Exception as e:
        current_app.logger.error("Error en /login/google/callback:\n" + traceback.format_exc())
        return (f"<pre>Error en el callback de Google:\n\n"
                f"{type(e).__name__}: {e}\n\n{traceback.format_exc()}</pre>"), 500


@auth_bp.route("/complete-registration", methods=["GET", "POST"])
def complete_registration():
    pending = session.get("pending_oauth")
    if not pending:
        return redirect("/")

    if request.method == "POST":
        phone = request.form.get("phone", "").strip()
        accepted_terms = request.form.get("accept_terms") == "on"

        errors = []
        if not phone:
            errors.append("El telefono es obligatorio.")
        if not accepted_terms:
            errors.append("Debes aceptar los Terminos y Condiciones para continuar.")

        if errors:
            return render_template("register.html", pending=pending, errors=errors,
                                    phone=phone, accept_terms=accepted_terms)

        # Aceptar los terminos incluye autorizar el uso del email para
        # campanias de marketing (ver texto del checkbox en register.html).
        user = User(
            google_id=pending["google_id"],
            email=pending["email"],
            name=pending["name"],
            avatar_url=pending["avatar_url"],
            phone=phone,
            accepted_terms_at=datetime.utcnow(),
            marketing_consent=True,
        )
        db.session.add(user)
        db.session.commit()

        session.pop("pending_oauth", None)
        session["user_id"] = user.id
        return redirect("/app")

    return render_template("register.html", pending=pending, errors=None,
                            phone="", accept_terms=False)


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect("/")
