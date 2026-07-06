import pytest

import app as app_module
import audit_log

BAND_SCORES = {"highly-human": 0.10, "uncertain": 0.55, "highly-AI": 0.93}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(audit_log, "LOG_DIR", tmp_path)
    monkeypatch.setattr(audit_log, "DB_PATH", tmp_path / "submissions.db")
    monkeypatch.setattr(audit_log, "APPEALS_PATH", tmp_path / "appeals.jsonl")
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as c:
        yield c


def fake_classify(band):
    """A classify() stand-in with a hand-set score, per M5's verification recipe:
    "construct three synthetic submissions whose scores are hand-set ... to land
    in each of the three bands."
    """
    score = BAND_SCORES[band]

    def _classify(text):
        return {
            "confidence": score,
            "label": band,
            "note": None,
            "signals": {
                "llm": {"score": score, "reasoning": f"{band} llm reasoning"},
                "stylometric": {"score": score, "explanation": f"{band} stylometric explanation"},
            },
        }

    return _classify


@pytest.mark.parametrize(
    "band, expected_snippet",
    [
        ("highly-human", "likely human-written"),
        ("uncertain", "not confident"),
        ("highly-AI", "likely AI-generated"),
    ],
)
def test_submit_and_get_render_the_correct_label_for_each_band(client, monkeypatch, band, expected_snippet):
    monkeypatch.setattr(app_module, "classify", fake_classify(band))

    resp = client.post("/submit", json={"text": "some text", "creator_id": "alice"})
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["label"] == band
    assert expected_snippet in body["message"]
    assert body["status"] == "final"

    fetched = client.get(f"/submissions/{body['content_id']}")
    assert fetched.status_code == 200
    assert expected_snippet in fetched.get_json()["message"]


def test_all_three_bands_produce_different_label_text(client, monkeypatch):
    messages = set()
    for band in BAND_SCORES:
        monkeypatch.setattr(app_module, "classify", fake_classify(band))
        resp = client.post("/submit", json={"text": f"{band} text"})
        messages.add(resp.get_json()["message"])
    assert len(messages) == 3


def test_appeal_flips_status_logs_and_rejects_second_attempt(client, monkeypatch):
    monkeypatch.setattr(app_module, "classify", fake_classify("highly-AI"))

    submitted = client.post("/submit", json={"text": "some text", "creator_id": "bob"}).get_json()
    content_id = submitted["content_id"]

    resp = client.post(f"/submissions/{content_id}/appeal", json={"reasoning": "I wrote this myself."})
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["status"] == "under_review"
    assert body["appeal"]["reasoning"] == "I wrote this myself."

    fetched = client.get(f"/submissions/{content_id}").get_json()
    assert fetched["status"] == "under_review"
    assert fetched["label"] == "highly-AI"
    assert fetched["confidence"] == submitted["confidence"]

    logged = client.get("/log?status=under_review").get_json()
    assert logged["count"] == 1
    assert logged["entries"][0]["content_id"] == content_id
    assert logged["entries"][0]["appeal"]["reasoning"] == "I wrote this myself."

    second_attempt = client.post(f"/submissions/{content_id}/appeal", json={"reasoning": "again"})
    assert second_attempt.status_code == 409


def test_appeal_requires_reasoning(client, monkeypatch):
    monkeypatch.setattr(app_module, "classify", fake_classify("uncertain"))
    submitted = client.post("/submit", json={"text": "some text"}).get_json()

    resp = client.post(f"/submissions/{submitted['content_id']}/appeal", json={"reasoning": "   "})
    assert resp.status_code == 400


def test_appeal_unknown_content_id_is_404(client):
    resp = client.post("/submissions/does-not-exist/appeal", json={"reasoning": "why not"})
    assert resp.status_code == 404


def test_log_filters_by_label(client, monkeypatch):
    monkeypatch.setattr(app_module, "classify", fake_classify("highly-human"))
    client.post("/submit", json={"text": "human text"})

    monkeypatch.setattr(app_module, "classify", fake_classify("highly-AI"))
    client.post("/submit", json={"text": "ai text"})

    logged = client.get("/log?label=highly-AI").get_json()
    assert logged["count"] == 1
    assert logged["entries"][0]["label"] == "highly-AI"
