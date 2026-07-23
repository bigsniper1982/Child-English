"""Family-password login, secure sessions, CSRF, rate limiting and route guards."""
import functools
import secrets
import time

from flask import (
    Blueprint, current_app, g, redirect, render_template, request,
    session, url_for, abort,
)
from werkzeug.security import check_password_hash

bp = Blueprint("auth", __name__)

# In-memory failed-login tracker: {ip: [timestamps]}. Fine for a single-family,
# single-process deployment; reset on process restart.
_attempts = {}


def _prune(ip, now, window):
    times = [t for t in _attempts.get(ip, []) if now - t < window]
    _attempts[ip] = times
    return times


def is_locked(ip):
    now = time.time()
    window = current_app.config["LOGIN_LOCKOUT_SECONDS"]
    times = _prune(ip, now, window)
    return len(times) >= current_app.config["MAX_LOGIN_ATTEMPTS"]


def record_failure(ip):
    _attempts.setdefault(ip, []).append(time.time())


def clear_failures(ip):
    _attempts.pop(ip, None)


def reset_rate_limits():
    """Test helper: forget all recorded login failures."""
    _attempts.clear()


# ---------------------------------------------------------------- CSRF --------
def get_csrf_token():
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


def validate_csrf():
    sent = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token")
    expected = session.get("csrf_token")
    if not expected or not sent or not secrets.compare_digest(sent, expected):
        abort(400, description="Invalid or missing CSRF token.")


# --------------------------------------------------------------- guards -------
def login_required(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def init_app(app):
    @app.before_request
    def csrf_protect():
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            validate_csrf()

    @app.context_processor
    def inject_csrf():
        return {"csrf_token": get_csrf_token()}


def _safe_next(value):
    """Allow only same-site absolute paths, never scheme-relative targets."""
    return bool(value and value.startswith("/")
                and not value.startswith("//")
                and not value.startswith("/\\"))


# --------------------------------------------------------------- routes -------
@bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("logged_in"):
        return redirect(url_for("main.today"))

    ip = request.remote_addr or "unknown"
    error = None

    if request.method == "POST":
        if is_locked(ip):
            return render_template("login.html", error=(
                "Too many tries. Please wait a few minutes and try again."
            )), 429
        password = request.form.get("password", "")
        pw_hash = current_app.config.get("FAMILY_PASSWORD_HASH")
        if pw_hash and check_password_hash(pw_hash, password):
            clear_failures(ip)
            session.clear()
            session["logged_in"] = True
            session.permanent = True
            get_csrf_token()
            nxt = request.args.get("next")
            if not _safe_next(nxt):
                nxt = url_for("main.today")
            return redirect(nxt)
        record_failure(ip)
        error = "That password is not right. Please try again."
        if is_locked(ip):
            return render_template("login.html", error=(
                "Too many tries. Please wait a few minutes and try again."
            )), 429

    return render_template("login.html", error=error)


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
