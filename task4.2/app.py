"""Task 4.2 - Simple Flask web application for Docker containerisation."""

import os
import re
import socket

from flask import Flask, jsonify, render_template_string, request

DEFAULT_PORT = 5000
MIN_PORT = 1
MAX_PORT = 65535
MAX_NAME_LENGTH = 50
BAD_REQUEST = 400

# Letters (including accented, e.g. Vietnamese) and single spaces only.
NAME_PATTERN = re.compile(r"^[^\W\d_]+(?: [^\W\d_]+)*$")

HOME_TEMPLATE = """<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>SWE40006 Task 4.2</title></head>
<body style="font-family: sans-serif; max-width: 40rem; margin: 3rem auto;">
  <h1>Hello from Flask in Docker!</h1>
  <p>SWE40006 Deployment Portfolio - Task 4.2</p>
  <p>Served by container / host: <strong>{{ hostname }}</strong></p>
</body>
</html>"""


def get_port() -> int:
    """Read the listening port from the PORT env variable, with validation."""
    raw_value = os.environ.get("PORT", str(DEFAULT_PORT))
    if not raw_value.isdigit():
        raise ValueError(f"PORT must be a number, got {raw_value!r}")
    port = int(raw_value)
    if not MIN_PORT <= port <= MAX_PORT:
        raise ValueError(f"PORT must be between {MIN_PORT} and {MAX_PORT}")
    return port


def validate_name(raw_name: str | None) -> str:
    """Return a cleaned name or raise ValueError describing the problem."""
    name = (raw_name or "").strip()
    if not name:
        raise ValueError("Query parameter 'name' is required")
    if len(name) > MAX_NAME_LENGTH:
        raise ValueError(f"Name must be at most {MAX_NAME_LENGTH} characters")
    if not NAME_PATTERN.match(name):
        raise ValueError("Name may only contain letters and single spaces")
    return name


def create_app() -> Flask:
    application = Flask(__name__)

    @application.get("/")
    def home():
        # render_template_string auto-escapes the value (XSS-safe).
        return render_template_string(HOME_TEMPLATE, hostname=socket.gethostname())

    @application.get("/health")
    def health():
        return jsonify(status="ok")

    @application.get("/api/greet")
    def greet():
        try:
            name = validate_name(request.args.get("name"))
        except ValueError as error:
            return jsonify(error=str(error)), BAD_REQUEST
        return jsonify(message=f"Hello, {name}!")

    return application


if __name__ == "__main__":
    # Bind to 0.0.0.0 so the app is reachable from outside the container.
    create_app().run(host="0.0.0.0", port=get_port())
