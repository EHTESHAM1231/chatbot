"""
User access log — records every signup and login with timestamp.

On local: writes to users_log.csv in the project root.
On Vercel: writes to /tmp/users_log.csv (persists within the same instance).

The CSV is also committed to the repo on each local run so you always
have a permanent record. Format:
    event, email, timestamp
"""

import os
import csv
from datetime import datetime, timezone

# Resolve log path: prefer project root, fall back to /tmp on read-only filesystems
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_LOCAL_PATH = os.path.join(_PROJECT_ROOT, "users_log.csv")
_TMP_PATH = "/tmp/users_log.csv"


def _get_log_path() -> str:
    """Return a writable path for the log file."""
    try:
        # Try writing to project root first
        with open(_LOCAL_PATH, "a"):
            pass
        return _LOCAL_PATH
    except OSError:
        return _TMP_PATH


def _write_event(event: str, email: str) -> None:
    """Append one row to the CSV log."""
    path = _get_log_path()
    file_exists = os.path.isfile(path)
    try:
        with open(path, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["event", "email", "timestamp"])
            writer.writerow([
                event,
                email,
                datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
            ])
    except OSError as e:
        # Non-fatal — log to console if file write fails
        print(f"[user_log] Could not write log: {e}")


def log_signup(email: str) -> None:
    """Record a new user registration."""
    _write_event("signup", email)


def log_login(email: str) -> None:
    """Record a successful login."""
    _write_event("login", email)
