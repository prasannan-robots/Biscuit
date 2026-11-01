import os
import secrets

from flask import Flask


def create_app():
    from .view import view

    app = Flask(__name__, static_folder="assets", static_url_path="/assets")
    # Sessions aren't used (the app is stateless), but Flask still wants a key.
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
    # Reject oversized uploads instead of reading them into memory.
    app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024
    app.register_blueprint(view)
    return app
