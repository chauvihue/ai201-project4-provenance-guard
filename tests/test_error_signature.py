import pytest

from stylometric_classifier_signal import (
    analyze_error_signature,
    find_grammar_issues,
    find_spelling_errors,
)

CLEAN_AI_TEXT = (
    "Artificial intelligence represents a transformative paradigm shift in modern society. "
    "It is important to note that while the benefits of AI are numerous, it is equally "
    "essential to consider the ethical implications."
)

CASUAL_HUMAN_TEXT = (
    "honestly idk how to start this but ok so yesterday my dog got into the trash AGAIN "
    "and istg he does it on purpose bcs he stares at me the whole time."
)

MISSPELLED_HUMAN_TEXT = (
    "I definately recieved the package yesterday, but the address was definately wrong "
    "and the whole situtation felt wierd to me."
)

GRAMMAR_NOISE_TEXT = (
    "I could of went to the store, but I forgot a apple at home. the the cat was hungry."
)

PRESSURE_MISSPELLINGS = [
    "occured",
    "seperate",
    "accomodate",
    "untill",
    "neccessary",
    "succesful",
    "becuase",
    "waht",
    "teh",
    "adn",
    "taht",
]


@pytest.mark.parametrize("misspelling", PRESSURE_MISSPELLINGS)
def test_detects_real_misspellings_outside_allowlist(misspelling: str):
    text = f"I think this word is wrong: {misspelling}."
    errors = find_spelling_errors(text)
    assert misspelling in [word.lower() for word in errors]


def test_clean_ai_text_has_no_spelling_or_grammar_flags():
    errors = find_spelling_errors(CLEAN_AI_TEXT)
    grammar = find_grammar_issues(CLEAN_AI_TEXT)
    assert errors == []
    assert grammar == []


def test_clean_ai_text_scores_polished_and_summary_is_accurate():
    result = analyze_error_signature(CLEAN_AI_TEXT)
    assert result["score"] >= 0.55
    assert result["spelling_errors"] == []
    assert result["grammar_issues"] == []
    assert "no spelling or grammar irregularities" in result["summary"]


def test_casual_human_text_detects_informal_markers_not_misspellings():
    result = analyze_error_signature(CASUAL_HUMAN_TEXT)
    assert result["score"] < 0.55
    assert "idk" in result["informal_markers"]
    assert "istg" in result["informal_markers"]
    assert "informal markers" in result["summary"]


def test_misspelled_human_text_detects_multiple_spelling_errors():
    result = analyze_error_signature(MISSPELLED_HUMAN_TEXT)
    assert result["score"] < 0.45
    lowered = [word.lower() for word in result["spelling_errors"]]
    assert "definately" in lowered
    assert "recieved" in lowered
    assert "wierd" in lowered
    assert "spelling irregularities" in result["summary"]


def test_grammar_noise_text_detects_common_grammar_issues():
    result = analyze_error_signature(GRAMMAR_NOISE_TEXT)
    grammar = find_grammar_issues(GRAMMAR_NOISE_TEXT)
    assert 'nonstandard "could of"' in grammar
    assert 'article "a" before vowel sound' in grammar
    assert "repeated word" in grammar
    assert result["score"] < 0.55
    assert "grammar issues" in result["summary"]


def test_proper_noun_is_not_flagged_as_misspelling():
    text = "Yesterday I visited CodePath in Brooklyn."
    errors = find_spelling_errors(text)
    assert errors == []


def test_explanation_uses_summary_not_misleading_error_signature_label():
    from stylometric_classifier_signal import classify_stylometric

    result = classify_stylometric(CLEAN_AI_TEXT)
    assert "high error signature" not in result["explanation"]
    assert "no spelling or grammar irregularities" in result["explanation"]
