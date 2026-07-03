import logging
import os
from datetime import timedelta
from functools import wraps

import requests
from dotenv import load_dotenv
from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

load_dotenv()

SECRET_TOKEN = os.getenv("SECRET_TOKEN")
PI_BASE_URL = os.getenv("PI_BASE_URL", "http://rpi-zero.local:8000")
FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY")

if not SECRET_TOKEN:
    raise RuntimeError("SECRET_TOKEN is not set in .env")
if not FLASK_SECRET_KEY:
    raise RuntimeError("FLASK_SECRET_KEY is not set in .env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = FLASK_SECRET_KEY
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=[],
    storage_uri="memory://",
)

REMEMBER_ME_DURATION = timedelta(days=7)


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("authenticated"):
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


# ---------------------------------------------------------------------------
# Auth routes
# ---------------------------------------------------------------------------

@app.route("/", methods=["GET"])
def index():
    if not session.get("authenticated"):
        return redirect(url_for("login"))
    return render_template("index.html")


@app.route("/login", methods=["GET"])
def login():
    if session.get("authenticated"):
        return redirect(url_for("index"))
    return render_template("login.html")


@app.route("/login", methods=["POST"])
@limiter.limit("10 per minute; 30 per hour")
def login_post():
    token = request.form.get("token", "").strip()
    remember = request.form.get("remember_me") == "on"

    if token != SECRET_TOKEN:
        logger.warning("Failed login attempt from %s", request.remote_addr)
        flash("Invalid token. Please try again.", "error")
        return render_template("login.html"), 401

    session.permanent = remember
    if remember:
        app.permanent_session_lifetime = REMEMBER_ME_DURATION
    session["authenticated"] = True
    logger.info("Successful login from %s (remember=%s)", request.remote_addr, remember)
    return redirect(url_for("index"))


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------------------------------------------------------------------------
# Proxy routes
# ---------------------------------------------------------------------------

@app.route("/toggle", methods=["POST"])
@login_required
@limiter.limit("20 per minute")
def toggle():
    try:
        resp = requests.post(
            f"{PI_BASE_URL}/toggle",
            headers={"x-token": SECRET_TOKEN},
            timeout=5,
        )
        resp.raise_for_status()
        logger.info("Garage toggled by session from %s", request.remote_addr)
        return jsonify({"status": "toggled"})
    except requests.exceptions.ConnectionError:
        logger.error("Toggle failed — could not connect to Pi at %s", PI_BASE_URL)
        return jsonify({
            "status": "error",
            "message": "Cannot reach the Pi.",
            "detail": "Connection refused or host unreachable."
                      "Check that the Pi is powered on, connected to the network, "
                      "and that PI_BASE_URL in .env is correct.",
            "code": "PI_UNREACHABLE",
        }), 502
    except requests.exceptions.Timeout:
        logger.error("Toggle failed — Pi at %s timed out after 5 s", PI_BASE_URL)
        return jsonify({
            "status": "error",
            "message": "Pi did not respond in time.",
            "detail": "The Pi accepted the connection but did not reply within 5 seconds. "
                      "It may be overloaded or the Flask process may have crashed. "
                      "Check the Pi's logs.",
            "code": "PI_TIMEOUT",
        }), 504
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code if e.response is not None else "unknown"
        logger.error("Toggle failed — Pi returned HTTP %s: %s", status_code, e)
        if status_code == 403:
            detail = (
                "The Pi rejected the request with 403 Forbidden. "
                "SECRET_TOKEN in this app's .env does not match the Pi's SECRET_TOKEN."
            )
        else:
            detail = f"The Pi returned HTTP {status_code}. Check the Pi's logs for details."
        return jsonify({
            "status": "error",
            "message": f"Pi returned HTTP {status_code}.",
            "detail": detail,
            "code": "PI_HTTP_ERROR",
        }), 502


@app.route("/api/status", methods=["GET"])
@login_required
def pi_status():
    try:
        resp = requests.get(
            f"{PI_BASE_URL}/status",
            headers={"x-token": SECRET_TOKEN},
            timeout=3,
        )
        resp.raise_for_status()
        return jsonify({"online": True})
    except requests.exceptions.ConnectionError:
        logger.warning("Status check — Pi unreachable at %s", PI_BASE_URL)
        return jsonify({
            "online": False,
            "reason": "Connection refused or host unreachable.",
            "detail": f"Could not connect to Pi. "
                      "Check that the Pi is on and PI_BASE_URL is correct.",
        })
    except requests.exceptions.Timeout:
        logger.warning("Status check — Pi at %s timed out", PI_BASE_URL)
        return jsonify({
            "online": False,
            "reason": "Pi did not respond within 3 seconds.",
            "detail": "The Pi may be overloaded or its Flask process may have crashed.",
        })
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code if e.response is not None else "unknown"
        logger.warning("Status check — Pi returned HTTP %s", status_code)
        detail = (
            "SECRET_TOKEN mismatch — check both .env files."
            if status_code == 403
            else f"Pi returned HTTP {status_code}."
        )
        return jsonify({
            "online": False,
            "reason": f"Pi returned HTTP {status_code}.",
            "detail": detail,
        })
    except Exception as e:
        logger.warning("Status check — unexpected error: %s", e)
        return jsonify({
            "online": False,
            "reason": "Unexpected error.",
            "detail": str(e),
        })


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    from waitress import serve
    logger.info("Starting Garag.io web server on http://0.0.0.0:8080")
    serve(app, host="0.0.0.0", port=8080)
