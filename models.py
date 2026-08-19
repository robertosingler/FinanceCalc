"""Modelos de base de datos: usuarios registrados, historial de calculos y
escenarios guardados. SQLite via Flask-SQLAlchemy."""

from datetime import datetime

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    google_id = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    name = db.Column(db.String(255))
    avatar_url = db.Column(db.String(512))
    phone = db.Column(db.String(32), nullable=False)
    accepted_terms_at = db.Column(db.DateTime, nullable=False)
    marketing_consent = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_login_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    history = db.relationship(
        "CalculationHistory", backref="user", cascade="all, delete-orphan",
        order_by="desc(CalculationHistory.created_at)",
    )
    saved = db.relationship(
        "SavedScenario", backref="user", cascade="all, delete-orphan",
        order_by="desc(SavedScenario.created_at)",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "avatar_url": self.avatar_url,
            "phone": self.phone,
            "marketing_consent": self.marketing_consent,
            "created_at": self.created_at.isoformat(),
        }


class CalculationHistory(db.Model):
    __tablename__ = "calculation_history"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)

    solved_field = db.Column(db.String(10), nullable=False)
    pv = db.Column(db.Float)
    pmt = db.Column(db.Float)
    fv = db.Column(db.Float)
    rate = db.Column(db.Float)
    n = db.Column(db.Float)
    freq = db.Column(db.Integer)
    rate_type = db.Column(db.String(16))
    mode = db.Column(db.String(8))
    decimals = db.Column(db.Integer)
    periodic_rate_pct = db.Column(db.Float)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "solved_field": self.solved_field,
            "pv": self.pv, "pmt": self.pmt, "fv": self.fv,
            "rate": self.rate, "n": self.n, "freq": self.freq,
            "rate_type": self.rate_type, "mode": self.mode,
            "decimals": self.decimals,
            "periodic_rate_pct": self.periodic_rate_pct,
            "created_at": self.created_at.isoformat(),
        }


class SavedScenario(db.Model):
    __tablename__ = "saved_scenario"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)

    name = db.Column(db.String(120), nullable=False)
    pv = db.Column(db.Float)
    pmt = db.Column(db.Float)
    fv = db.Column(db.Float)
    rate = db.Column(db.Float)
    n = db.Column(db.Float)
    freq = db.Column(db.Integer)
    rate_type = db.Column(db.String(16))
    mode = db.Column(db.String(8))
    decimals = db.Column(db.Integer)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "pv": self.pv, "pmt": self.pmt, "fv": self.fv,
            "rate": self.rate, "n": self.n, "freq": self.freq,
            "rate_type": self.rate_type, "mode": self.mode,
            "decimals": self.decimals,
            "created_at": self.created_at.isoformat(),
        }
