"""
Authentication logic: registration, login, validation, and route protection.

Keeps all auth concerns separate from chatbot logic.
"""

import re
import bcrypt
from functools import wraps
from flask import redirect, url_for, flash
from flask_login import LoginManager, current_user

from src.models import db, User

# ── Flask-Login setup ────────────────────────────────────────────────────────

login_manager = LoginManager()
login_manager.login_view = "login_page"          # redirect here if @login_required fails
login_manager.login_message = "Please log in to access the chatbot."
login_manager.login_message_category = "info"


@login_manager.user_loader
def load_user(user_id: str):
    """Tell Flask-Login how to reload a user from the session."""
    return db.session.get(User, int(user_id))


# ── Validation helpers ───────────────────────────────────────────────────────

EMAIL_RE = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")

# Password rules: min 8 chars, at least one uppercase, one digit, one special char
PASSWORD_RE = re.compile(r"^(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]).{8,}$")


def validate_email(email: str) -> str | None:
    """Return an error string or None if valid."""
    if not email or not email.strip():
        return "Email is required."
    if not EMAIL_RE.match(email.strip()):
        return "Invalid email format."
    return None


def validate_password(password: str) -> str | None:
    """Return an error string or None if valid."""
    if not password:
        return "Password is required."
    if len(password) < 8:
        return "Password must be at least 8 characters."
    if not re.search(r"[A-Z]", password):
        return "Password must contain at least one uppercase letter."
    if not re.search(r"\d", password):
        return "Password must contain at least one number."
    if not re.search(r"[!@#$%^&*()_+\-=\[\]{};':\"\\|,.<>\/?]", password):
        return "Password must contain at least one special character."
    return None


# ── Core auth functions ──────────────────────────────────────────────────────

def register_user(email: str, password: str) -> tuple[bool, str]:
    """Register a new user.

    Returns:
        (True, "success message") on success
        (False, "error message") on failure
    """
    email = email.strip().lower()

    err = validate_email(email)
    if err:
        return False, err

    err = validate_password(password)
    if err:
        return False, err

    if User.query.filter_by(email=email).first():
        return False, "An account with this email already exists."

    # Hash password with bcrypt (auto-generates salt)
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

    user = User(email=email, password_hash=hashed.decode("utf-8"))
    db.session.add(user)
    db.session.commit()

    return True, "Account created successfully. Please log in."


def authenticate_user(email: str, password: str) -> tuple[User | None, str]:
    """Verify credentials and return the User object.

    Returns:
        (User, "") on success
        (None, "error message") on failure
    """
    email = email.strip().lower()

    if not email or not password:
        return None, "Email and password are required."

    user = User.query.filter_by(email=email).first()
    if not user:
        # Same message as wrong password — avoids user enumeration
        return None, "Invalid email or password."

    if not bcrypt.checkpw(password.encode("utf-8"), user.password_hash.encode("utf-8")):
        return None, "Invalid email or password."

    return user, ""
