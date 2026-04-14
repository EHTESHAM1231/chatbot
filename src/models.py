"""
Database models for user authentication.
Uses Flask-SQLAlchemy with SQLite (easily swappable to PostgreSQL).
"""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

# Single shared db instance — imported by app.py and auth.py
db = SQLAlchemy()


class User(UserMixin, db.Model):
    """User account model.

    Inherits UserMixin to satisfy Flask-Login's required interface:
    is_authenticated, is_active, is_anonymous, get_id().
    """

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    # Stores bcrypt hash — never plain text
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<User {self.email}>"
