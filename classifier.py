"""Public entry point: runs both signals and returns a combined classification."""

from llm_classifier_signal import (
    NOTE_HIGH_BOUNDARY,
    NOTE_LOW_BOUNDARY,
    classify_llm,
    score_submission,
)
from stylometric_classifier_signal import FEATURE_SUBSCORERS, classify_stylometric

__all__ = [
    "classify",
    "classify_llm",
    "classify_stylometric",
    "score_submission",
    "FEATURE_SUBSCORERS",
    "NOTE_HIGH_BOUNDARY",
    "NOTE_LOW_BOUNDARY",
]


def classify(text: str) -> dict:
    """Runs every classification signal on `text` and combines them per planning.md."""
    llm_result = classify_llm(text)
    stylometric_result = classify_stylometric(text)
    scored = score_submission(llm_result, stylometric_result)

    return {
        "confidence": scored["confidence"],
        "label": scored["label"],
        "note": scored["note"],
        "attribution": scored["label"],
        "signals": scored["signals"],
    }
