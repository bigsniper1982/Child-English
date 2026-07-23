"""Application factory for 英语冒险岛 (English Adventure Island)."""
import os
import secrets

from flask import Flask, render_template
from werkzeug.middleware.proxy_fix import ProxyFix


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    # The production service only listens on loopback behind one trusted Nginx
    # proxy. Trust exactly one forwarded hop so per-IP rate limiting works.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

    app.config.from_mapping(
        SECRET_KEY=os.environ.get("SECRET_KEY") or secrets.token_hex(32),
        DATABASE=os.environ.get("DATABASE",
                                os.path.join(app.instance_path, "app.db")),
        FAMILY_PASSWORD_HASH=os.environ.get("FAMILY_PASSWORD_HASH"),
        MAX_LOGIN_ATTEMPTS=int(os.environ.get("MAX_LOGIN_ATTEMPTS", "5")),
        LOGIN_LOCKOUT_SECONDS=int(os.environ.get("LOGIN_LOCKOUT_SECONDS", "300")),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE", "0") == "1",
        PERMANENT_SESSION_LIFETIME=60 * 60 * 24 * 30,
    )

    if test_config:
        app.config.update(test_config)

    os.makedirs(app.instance_path, exist_ok=True)

    from app import db, auth, routes
    db.init_app(app)
    auth.init_app(app)
    app.register_blueprint(auth.bp)
    app.register_blueprint(routes.bp)

    # Create the schema / default child on first use.
    with app.app_context():
        db.init_db()

    register_error_handlers(app)
    return app


def register_error_handlers(app):
    @app.errorhandler(400)
    def bad_request(e):
        return render_template("error.html", code=400,
                               message="Something looked wrong with that request."), 400

    @app.errorhandler(403)
    def forbidden(e):
        return render_template("error.html", code=403,
                               message="You need to log in first."), 403

    @app.errorhandler(404)
    def not_found(e):
        return render_template("error.html", code=404,
                               message="We couldn't find that page."), 404

    @app.errorhandler(429)
    def too_many(e):
        return render_template("error.html", code=429,
                               message="Too many tries. Please wait a moment."), 429

    @app.errorhandler(500)
    def server_error(e):
        return render_template("error.html", code=500,
                               message="Oops! Something went wrong on our island."), 500
