import os
import secrets
import threading
import time
from collections import defaultdict, deque

from flask import Flask, jsonify, make_response, render_template, request, send_from_directory

from analyzer import analyze

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OCR_LANG_DIR = os.path.join(BASE_DIR, "ocr_lang")

app = Flask(__name__)

MAX_LENGTH = 5000                                  # maximum characters analysed per message
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024       # reject request bodies larger than 64 KB
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 604800   # browsers keep fonts / scripts for 7 days

# ---------- simple rate limiter (per visitor, in memory) ----------
# Many users can share one public IP (college Wi-Fi), so the default is generous.
RATE_LIMIT = int(os.environ.get("RATE_LIMIT", "120"))   # requests allowed ...
RATE_WINDOW = 60                                         # ... per this many seconds
_hits = defaultdict(deque)
_lock = threading.Lock()


def client_ip():
    forwarded = request.headers.get("X-Forwarded-For", "")
    return (forwarded.split(",")[0].strip() if forwarded else request.remote_addr) or "unknown"


def is_rate_limited(ip):
    now = time.time()
    with _lock:
        q = _hits[ip]
        while q and now - q[0] > RATE_WINDOW:
            q.popleft()
        if len(q) >= RATE_LIMIT:
            return True
        q.append(now)
        if len(_hits) > 5000:          # keep memory small
            for key in [k for k, v in _hits.items() if not v or now - v[-1] > RATE_WINDOW]:
                del _hits[key]
        return False


# ---------- security headers ----------
@app.after_request
def add_security_headers(resp):
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "no-referrer"
    resp.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=()"
    resp.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    if request.headers.get("X-Forwarded-Proto", request.scheme) == "https":
        resp.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    if request.path.startswith("/api/"):
        resp.headers["Cache-Control"] = "no-store"
    return resp


def csp(nonce):
    # images are read in the browser (OCR), so the page needs blob: images and a same-origin worker
    return (
        "default-src 'none'; "
        f"script-src 'nonce-{nonce}' 'self' 'wasm-unsafe-eval'; "
        f"style-src 'nonce-{nonce}'; "
        "font-src 'self'; "
        "connect-src 'self' blob: data:; "
        "img-src 'self' data: blob:; "
        "media-src 'self' data: blob:; "
        "worker-src 'self' blob:; "
        "base-uri 'none'; form-action 'none'; frame-ancestors 'none'; object-src 'none'"
    )


# ---------- routes ----------
@app.route("/")
def home():
    nonce = secrets.token_urlsafe(16)
    resp = make_response(render_template("index.html", nonce=nonce))
    resp.headers["Content-Security-Policy"] = csp(nonce)
    resp.headers["Cache-Control"] = "no-cache"
    return resp


@app.route("/ocr-data/<path:name>")
def ocr_data(name):
    # language files for the in-browser image reader (served as plain bytes on purpose,
    # so the browser does not try to un-gzip them a second time)
    return send_from_directory(OCR_LANG_DIR, name, mimetype="application/octet-stream")


@app.route("/api/analyze", methods=["POST"])
def api_analyze():
    if is_rate_limited(client_ip()):
        return jsonify(error="rate_limited"), 429
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error="bad_request"), 400
    message = data.get("message", "")
    if not isinstance(message, str):
        return jsonify(error="bad_request"), 400
    lang = data.get("lang", "en")
    return jsonify(analyze(message[:MAX_LENGTH], lang if isinstance(lang, str) else "en"))


# ---------- safe error pages (no technical details leaked) ----------
@app.errorhandler(404)
def not_found(e):
    return jsonify(error="not_found"), 404


@app.errorhandler(405)
def not_allowed(e):
    return jsonify(error="method_not_allowed"), 405


@app.errorhandler(413)
def too_large(e):
    return jsonify(error="too_large"), 413


@app.errorhandler(500)
def server_error(e):
    return jsonify(error="server_error"), 500


if __name__ == "__main__":
    # host 0.0.0.0 lets other devices on the same Wi-Fi open it
    app.run(host="0.0.0.0", port=5000, debug=False)
