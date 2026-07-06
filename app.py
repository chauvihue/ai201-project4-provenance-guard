import uuid
from datetime import datetime, timezone

from flask import Flask, jsonify, request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from classifier import classify
from audit_log import file_appeal, get_appeal, get_log, get_submission, log_entry, update_status
from labels import pick_driving_signal, render_label

MAX_CONTENT_LENGTH_CHARS = 20_000

app = Flask(__name__)
limiter = Limiter(get_remote_address, app=app, default_limits=[])


@app.errorhandler(429)
def handle_rate_limit(_e):
    return jsonify({"error": "rate limit exceeded, try again later"}), 429


def _to_response(entry: dict) -> dict:
    """Shapes a stored entry into the documented API response, appeal included."""
    response = {
        "content_id": entry["content_id"],
        "creator_id": entry["creator_id"],
        "submitted_at": entry["submitted_at"],
        "label": entry["label"],
        "confidence": entry["confidence"],
        "note": entry["note"],
        "message": entry.get("message"),
        "llm_score": entry["llm_score"],
        "llm_reasoning": entry["llm_reasoning"],
        "stylometric_score": entry["stylometric_score"],
        "stylometric_explanation": entry["stylometric_explanation"],
        "status": entry["status"],
    }
    response["appeal"] = get_appeal(entry["content_id"])
    return response


@app.post("/submit")
# 10/min covers a writer iterating on several drafts/paragraphs in one sitting;
# 100/day covers a heavy user across a full day while still bounding a scripted flood
# (the LLM signal calls a paid, rate-limited API on every request, so this is the one
# route that needs a hard ceiling -- see README for the full reasoning).
@limiter.limit("10 per minute; 100 per day")
def submit():
    body = request.get_json(silent=True) or {}
    text = body.get("text")
    creator_id = body.get("creator_id") or "anonymous"

    if not text or not text.strip():
        return jsonify({"error": "text is required and cannot be empty"}), 400
    if len(text) > MAX_CONTENT_LENGTH_CHARS:
        return jsonify({"error": f"text exceeds max length of {MAX_CONTENT_LENGTH_CHARS} characters"}), 400

    classification_result = classify(text)
    signals = classification_result["signals"]
    driving_signal = pick_driving_signal(signals)
    message = render_label(
        classification_result["label"],
        classification_result["confidence"],
        classification_result["note"],
        driving_signal,
    )

    result = {
        "content_id": str(uuid.uuid4()),
        "creator_id": creator_id,
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "text": text,
        "label": classification_result["label"],
        "confidence": classification_result["confidence"],
        "note": classification_result["note"],
        "message": message,
        "llm_score": signals["llm"]["score"],
        "llm_reasoning": signals["llm"]["reasoning"],
        "stylometric_score": signals["stylometric"]["score"],
        "stylometric_explanation": signals["stylometric"]["explanation"],
        "status": "final",
    }
    log_entry(result)

    return jsonify(_to_response(result)), 201


@app.get("/submissions/<content_id>")
def get_submission_route(content_id):
    entry = get_submission(content_id)
    if entry is None:
        return jsonify({"error": "no submission found for that content_id"}), 404
    return jsonify(_to_response(entry))


@app.post("/submissions/<content_id>/appeal")
def appeal(content_id):
    entry = get_submission(content_id)
    if entry is None:
        return jsonify({"error": "no submission found for that content_id"}), 404

    if get_appeal(content_id) is not None:
        return jsonify({"error": "an appeal has already been filed for this submission"}), 409

    body = request.get_json(silent=True) or {}
    reasoning = body.get("reasoning")
    if not reasoning or not reasoning.strip():
        return jsonify({"error": "reasoning is required and cannot be empty"}), 400

    appeal_record = file_appeal(content_id, reasoning)
    update_status(content_id, "under_review")

    return jsonify({
        "content_id": content_id,
        "status": "under_review",
        "appeal": {"reasoning": appeal_record["reasoning"], "filed_at": appeal_record["filed_at"]},
    })


@app.get("/log")
def log():
    status = request.args.get("status")
    label = request.args.get("label")
    limit = request.args.get("limit", default=50, type=int)

    entries = get_log(limit=limit, status=status, label=label)
    return jsonify({
        "count": len(entries),
        "entries": [_to_response(entry) for entry in entries],
    })


if __name__ == "__main__":
    app.run(debug=True)
