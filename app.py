import uuid
from datetime import datetime, timezone

from flask import Flask, jsonify, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from classifier import classify
from audit_log import log_entry, get_log

MAX_CONTENT_LENGTH_CHARS = 20_000

app = Flask(__name__)
limiter = Limiter(get_remote_address, app=app, default_limits=[])


@app.errorhandler(429)
def handle_rate_limit(_e):
    return jsonify({"error": "rate limit exceeded, try again later"}), 429


@app.post("/submit")
@limiter.limit("10 per minute")
def submit():
    body = request.get_json(silent=True) or {}
    text = body.get("text")
    creator_id = body.get("creator_id") or "anonymous"

    print(text)

    if not text or not text.strip():
        return jsonify({"error": "text is required and cannot be empty"}), 400
    if len(text) > MAX_CONTENT_LENGTH_CHARS:
        return jsonify({"error": f"text exceeds max length of {MAX_CONTENT_LENGTH_CHARS} characters"}), 400

    classification_result = classify(text)

    # TODO (M5): render_label(), persist to submissions.db, wire up appeals

    result = {
        "content_id": str(uuid.uuid4()),
        "creator_id": creator_id,
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "label": classification_result["label"],
        "confidence": classification_result["confidence"],
        "note": classification_result["note"],
        "attribution": classification_result["signals"],
        "status": "classified",
    }
    log_entry(result)

    return jsonify(result), 201


@app.get("/log")
def log():
    return jsonify({"entries": get_log()})


if __name__ == "__main__":
    app.run(debug=True)
