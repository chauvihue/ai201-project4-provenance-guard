"""Display-layer label rendering per planning.md's "Displayed label text" section.

`score_submission` (llm_classifier_signal.py) produces the internal label id
(`highly-human` / `highly-AI` / `uncertain`) and, for boundary scores, a NOTE
string. This module turns those into the exact reader-facing sentence.
"""

HIGHLY_AI_TEMPLATE = (
    "This content is **likely AI-generated**. Our analysis found strong AI "
    "fingerprints across most of the text, including {driving_signal}."
)

HIGHLY_HUMAN_TEXT = (
    "This content is **likely human-written**. Our analysis found the natural "
    "variation and irregularity typical of unassisted writing, with no strong "
    "AI fingerprint detected."
)

UNCERTAIN_TEXT = (
    "We're **not confident** whether this content is AI-generated or "
    "human-written. The analysis found a mix of signals — some consistent "
    "with AI generation, some consistent with human writing — so we can't "
    "make a clean call. Treat this classification as inconclusive."
)

DEFAULT_DRIVING_SIGNAL = "uniform sentence structure and heavy use of common AI phrasing"


MAX_DRIVING_SIGNAL_CHARS = 140


def _first_sentence(text: str) -> str:
    """Shortens a full reasoning paragraph down to a one-line "why"."""
    first = text.strip().split(". ")[0].rstrip(".")
    if len(first) > MAX_DRIVING_SIGNAL_CHARS:
        first = first[:MAX_DRIVING_SIGNAL_CHARS].rsplit(" ", 1)[0]
    return first


def pick_driving_signal(signals: dict) -> str:
    """Picks whichever signal's score is more decisive (farther from 0.5) and
    returns a one-line summary of its explanation, so the highly-AI template's
    bracket is filled with the evidence that actually drove the call rather
    than a placeholder.
    """
    llm = signals.get("llm", {})
    stylometric = signals.get("stylometric", {})

    llm_distance = abs(llm.get("score", 0.5) - 0.5)
    stylometric_distance = abs(stylometric.get("score", 0.5) - 0.5)

    if llm_distance >= stylometric_distance:
        explanation = llm.get("reasoning")
    else:
        explanation = stylometric.get("explanation")

    return _first_sentence(explanation) if explanation else DEFAULT_DRIVING_SIGNAL


def render_label(label: str, confidence: float, note: str | None, driving_signal: str = "") -> str:
    """Renders the exact reader-facing label text for `label`, followed by the
    numeric confidence and (for highly-human/uncertain) a one-line "why".
    Boundary-band `note` text is appended verbatim, per planning.md.
    """
    if label == "highly-AI":
        sentence = HIGHLY_AI_TEMPLATE.format(driving_signal=driving_signal or DEFAULT_DRIVING_SIGNAL)
        why = None
    elif label == "highly-human":
        sentence = HIGHLY_HUMAN_TEXT
        why = driving_signal or None
    elif label == "uncertain":
        sentence = UNCERTAIN_TEXT
        why = driving_signal or None
    else:
        raise ValueError(f"unknown label: {label!r}")

    parts = [sentence, f"Confidence: {round(confidence * 100)}%."]
    if why:
        parts.append(why.rstrip(".") + ".")
    if note:
        parts.append(note)
    return " ".join(parts)
