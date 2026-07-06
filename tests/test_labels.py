import pytest

from labels import HIGHLY_HUMAN_TEXT, UNCERTAIN_TEXT, pick_driving_signal, render_label
from llm_classifier_signal import NOTE_HIGH_BOUNDARY, NOTE_LOW_BOUNDARY


def test_highly_human_label_is_verbatim_and_unmodified():
    text = render_label("highly-human", 0.05, None)
    assert text.startswith(HIGHLY_HUMAN_TEXT)


def test_uncertain_label_is_verbatim_and_unmodified():
    text = render_label("uncertain", 0.55, None)
    assert text.startswith(UNCERTAIN_TEXT)


def test_highly_ai_label_interpolates_driving_signal():
    text = render_label("highly-AI", 0.93, None, driving_signal="repetitive hedging phrases")
    assert text.startswith("This content is **likely AI-generated**.")
    assert "repetitive hedging phrases" in text


def test_unknown_label_raises():
    with pytest.raises(ValueError):
        render_label("not-a-real-label", 0.5, None)


@pytest.mark.parametrize(
    "label, confidence",
    [("highly-human", 0.10), ("uncertain", 0.55), ("highly-AI", 0.93)],
)
def test_confidence_percentage_is_appended(label, confidence):
    text = render_label(label, confidence, None)
    assert f"Confidence: {round(confidence * 100)}%." in text


def test_three_variants_are_reachable_and_distinct():
    """The label text must change with the score, not stay constant regardless of it."""
    human = render_label("highly-human", 0.10, None)
    uncertain = render_label("uncertain", 0.55, None)
    ai = render_label("highly-AI", 0.93, None, driving_signal="uniform structure")

    variants = {human, uncertain, ai}
    assert len(variants) == 3


@pytest.mark.parametrize(
    "confidence, note",
    [
        (0.74, NOTE_HIGH_BOUNDARY),
        (0.22, NOTE_LOW_BOUNDARY),
    ],
)
def test_boundary_note_is_appended_to_the_label_text(confidence, note):
    label = "uncertain" if 0.25 < confidence < 0.80 else ("highly-human" if confidence <= 0.25 else "highly-AI")
    text = render_label(label, confidence, note)
    assert text.endswith(note)


def test_no_note_when_confidence_is_outside_boundary_bands():
    text = render_label("highly-human", 0.05, None)
    assert "NOTE" not in text


def test_pick_driving_signal_uses_the_more_decisive_score():
    signals = {
        "llm": {"score": 0.95, "reasoning": "llm reasoning text"},
        "stylometric": {"score": 0.55, "explanation": "stylometric explanation text"},
    }
    assert pick_driving_signal(signals) == "llm reasoning text"

    signals = {
        "llm": {"score": 0.55, "reasoning": "llm reasoning text"},
        "stylometric": {"score": 0.05, "explanation": "stylometric explanation text"},
    }
    assert pick_driving_signal(signals) == "stylometric explanation text"
