"""
Vercel serverless entry point — full Flask app with authentication.
"""
import os
import sys

# Add project root to path so src/ imports work
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_cors import CORS
from flask_login import login_user, logout_user, login_required, current_user

from src.models import db, User
from src.auth import login_manager, register_user, authenticate_user
from src.user_log import log_signup, log_login
from src.config import Config, ConfigurationError
from src.chatbot import Chatbot

# ── App setup ────────────────────────────────────────────────────────────────

app = Flask(
    __name__,
    template_folder=os.path.join(ROOT, "templates"),
    static_folder=os.path.join(ROOT, "static"),
)
CORS(app)

app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "change-me-in-production")
# On Vercel use /tmp (writable); locally use project root
db_path = os.getenv("DATABASE_URL", f"sqlite:////tmp/chatbot_users.db")
app.config["SQLALCHEMY_DATABASE_URI"] = db_path
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)
login_manager.init_app(app)

with app.app_context():
    db.create_all()

# ── Chatbot ──────────────────────────────────────────────────────────────────

chatbot = None
_init_error = None
try:
    config = Config.from_env()
    chatbot = Chatbot(config)
except ConfigurationError as e:
    _init_error = str(e)
    print(f"Configuration error: {_init_error}")
except Exception as e:
    _init_error = str(e)
    print(f"Initialization error: {_init_error}")

# ── Auth routes ──────────────────────────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
def login_page():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        user, error = authenticate_user(email, password)
        if user:
            login_user(user, remember=True)
            log_login(email)
            return redirect(request.args.get("next") or url_for("index"))
        flash(error, "error")
    return render_template("login.html")


@app.route("/signup", methods=["GET", "POST"])
def signup_page():
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
            log_signup(email)
            flash(message, "success")
            return redirect(url_for("login_page"))
        flash(message, "error")
    return render_template("signup.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("login_page"))


# ── Chatbot routes ───────────────────────────────────────────────────────────

@app.route("/")
@login_required
def index():
    return render_template("index.html")


@app.route("/api/chat", methods=["POST"])
@login_required
def chat():
    if chatbot is None:
        return jsonify({"success": False, "error": f"Chatbot not configured: {_init_error}"}), 500
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
    try:
        chatbot.conversation_store.clear_history()
        return jsonify({"success": True, "message": "Conversation history cleared"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
