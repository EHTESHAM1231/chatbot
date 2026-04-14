"""
Flask Web Application for LLM Chatbot with Authentication.

Routes:
    GET  /           → chatbot UI (login required)
    GET  /login      → login page
    POST /login      → process login
    GET  /signup     → signup page
    POST /signup     → process registration
    GET  /logout     → logout and redirect to login
    POST /api/chat   → chatbot endpoint (login required)
    POST /api/clear  → clear conversation history (login required)
"""

import os
import sys
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_cors import CORS
from flask_login import login_user, logout_user, login_required, current_user

from src.models import db, User
from src.auth import login_manager, register_user, authenticate_user
from src.config import Config, ConfigurationError
from src.chatbot import Chatbot

# ── App factory ──────────────────────────────────────────────────────────────

app = Flask(__name__)
CORS(app)

# Secret key for session signing — override via SECRET_KEY env var in production
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "change-me-in-production-use-a-long-random-string")

# SQLite database stored in project root
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///chatbot_users.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialise extensions
db.init_app(app)
login_manager.init_app(app)

# Create tables on first run
with app.app_context():
    db.create_all()

# ── Chatbot initialisation ───────────────────────────────────────────────────

try:
    config = Config.from_env()
    chatbot = Chatbot(config)
except ConfigurationError as e:
    print(f"Configuration error: {str(e)}")
    sys.exit(1)

# ── Auth routes ──────────────────────────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
def login_page():
    """Show login form (GET) or process credentials (POST)."""
    # Already logged in — go straight to chatbot
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        user, error = authenticate_user(email, password)
        if user:
            login_user(user, remember=True)   # session persists across browser restarts
            # Honour the original destination if Flask-Login set one
            next_page = request.args.get("next")
            return redirect(next_page or url_for("index"))
        else:
            flash(error, "error")

    return render_template("login.html")


@app.route("/signup", methods=["GET", "POST"])
def signup_page():
    """Show signup form (GET) or create account (POST)."""
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm", "")

        if password != confirm:
            flash("Passwords do not match.", "error")
            return render_template("signup.html")

        success, message = register_user(email, password)
        if success:
            flash(message, "success")
            return redirect(url_for("login_page"))
        else:
            flash(message, "error")

    return render_template("signup.html")


@app.route("/logout")
@login_required
def logout():
    """Log out the current user and redirect to login."""
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("login_page"))


# ── Chatbot routes (protected) ───────────────────────────────────────────────

@app.route("/")
@login_required
def index():
    """Render the main chat interface — only for authenticated users."""
    return render_template("index.html")


@app.route("/api/chat", methods=["POST"])
@login_required
def chat():
    """Process a chat message and return the LLM response."""
    try:
        data = request.get_json()
        user_message = data.get("message", "").strip()

        if not user_message:
            return jsonify({"success": False, "error": "Please provide a valid message"}), 400

        response = chatbot.process_query(user_message)
        return jsonify({"success": True, "response": response})

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/clear", methods=["POST"])
@login_required
def clear_history():
    """Clear the in-memory conversation history."""
    try:
        chatbot.conversation_store.clear_history()
        return jsonify({"success": True, "message": "Conversation history cleared"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ── Dev runner ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3000, debug=True)
