import pytest

from llm_classifier_signal import NOTE_HIGH_BOUNDARY, NOTE_LOW_BOUNDARY, score_submission

HUMAN_TEXT_LLM = {"score": 0.05, "reasoning": "casual irregular human voice"}
AI_TEXT_LLM = {"score": 0.93, "reasoning": "uniform polished AI prose"}
MIXED_TEXT_LLM = {"score": 0.55, "reasoning": "localized AI filler in personal essay"}

HUMAN_TEXT_STYLO = {"score": 0.18, "explanation": "high burstiness, informal error signature"}
AI_TEXT_STYLO = {"score": 0.82, "explanation": "low burstiness, lexical diversity tells"}
MIXED_TEXT_STYLO = {"score": 0.48, "explanation": "mixed stylometric features"}
ESL_TEXT_STYLO = {"score": 0.62, "explanation": "formal transitions and low error signature"}


@pytest.mark.parametrize(
    "confidence, expected_label",
    [
        (0.25, "highly-human"),
        (0.20, "highly-human"),
        (0.251, "uncertain"),
        (0.79, "uncertain"),
        (0.80, "highly-AI"),
        (0.95, "highly-AI"),
    ],
)
def test_label_thresholds_match_planning_spec(confidence, expected_label):
    llm_score = confidence
    stylo_score = confidence
    result = score_submission({"score": llm_score, "reasoning": "x"}, {"score": stylo_score, "explanation": "y"})
    assert result["label"] == expected_label
    assert result["confidence"] == pytest.approx(confidence)


def test_combined_score_uses_equal_weights():
    result = score_submission(
        {"score": 0.90, "reasoning": "ai"},
        {"score": 0.20, "explanation": "human"},
    )
    assert result["confidence"] == pytest.approx(0.55)


@pytest.mark.parametrize(
    "llm_score, stylo_score, expect_note",
    [
        (0.74, 0.74, NOTE_HIGH_BOUNDARY),
        (0.70, 0.70, NOTE_HIGH_BOUNDARY),
        (0.85, 0.85, NOTE_HIGH_BOUNDARY),
        (0.22, 0.22, NOTE_LOW_BOUNDARY),
        (0.30, 0.30, NOTE_LOW_BOUNDARY),
        (0.69, 0.69, None),
        (0.86, 0.86, None),
        (0.19, 0.19, None),
        (0.31, 0.31, None),
    ],
)
def test_boundary_note_bands(llm_score, stylo_score, expect_note):
    result = score_submission(
        {"score": llm_score, "reasoning": "x"},
        {"score": stylo_score, "explanation": "y"},
    )
    assert result["note"] == expect_note


def test_end_to_end_scoring_on_four_curated_inputs():
    cases = [
        ("human", HUMAN_TEXT_LLM, HUMAN_TEXT_STYLO, "highly-human"),
        ("ai", AI_TEXT_LLM, AI_TEXT_STYLO, "highly-AI"),
        ("mixed", MIXED_TEXT_LLM, MIXED_TEXT_STYLO, "uncertain"),
        ("esl", {"score": 0.45, "reasoning": "formal ESL connectors"}, ESL_TEXT_STYLO, "uncertain"),
    ]

    confidences = []
    for name, llm, stylo, expected_label in cases:
        result = score_submission(llm, stylo)
        confidences.append(result["confidence"])
        assert result["label"] == expected_label, f"{name}: {result}"

    assert max(confidences) - min(confidences) >= 0.35
