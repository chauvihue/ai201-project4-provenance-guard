"""Signal 2: lightweight stylometric heuristics (no LLM call)."""

from __future__ import annotations

import re
from functools import lru_cache
from statistics import mean, pstdev

from spellchecker import SpellChecker

# --- Error signature (spelling / grammar irregularities) ---

INFORMAL_ALLOWLIST = frozenset(
    {
        "idk",
        "lol",
        "istg",
        "bcs",
        "bc",
        "gonna",
        "wanna",
        "tbh",
        "imo",
        "ngl",
        "anyways",
        "honestly",
        "ok",
        "omg",
        "smh",
        "fyi",
        "irl",
        "afaik",
        "pls",
        "thx",
        "u",
        "ur",
        "ya",
        "yall",
        "y'all",
        "kinda",
        "sorta",
        "dunno",
        "lemme",
        "gimme",
        "min",
        "mins",
        "sec",
        "secs",
    }
)

GRAMMAR_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\bcould of\b", re.IGNORECASE), 'nonstandard "could of"'),
    (re.compile(r"\bshould of\b", re.IGNORECASE), 'nonstandard "should of"'),
    (re.compile(r"\bwould of\b", re.IGNORECASE), 'nonstandard "would of"'),
    (re.compile(r"\bmust of\b", re.IGNORECASE), 'nonstandard "must of"'),
    (re.compile(r"\balot\b", re.IGNORECASE), 'nonstandard "alot"'),
    (re.compile(r"\binformations\b", re.IGNORECASE), 'nonstandard plural "informations"'),
    (re.compile(r"\b(a) ([aeiouAEIOU]\w*)", re.IGNORECASE), 'article "a" before vowel sound'),
    (re.compile(r"\b(\w+)\s+\1\b", re.IGNORECASE), "repeated word"),
    (re.compile(r"\b(?:is|are|was|were)\s+(?:more|less)\s+(?:better|worse)\b", re.IGNORECASE), "double comparative"),
    (re.compile(r"\b(?:the\s+){2,}", re.IGNORECASE), "repeated article"),
)

COMMON_MISSPELLINGS = frozenset(
    {
        "recieve",
        "definately",
        "occured",
        "seperate",
        "accomodate",
        "untill",
        "wierd",
        "thier",
        "freind",
        "beleive",
        "goverment",
        "enviroment",
        "neccessary",
        "succesful",
        "tommorow",
        "tommorrow",
        "basicly",
        "probaly",
        "probly",
        "becuase",
        "becasue",
        "waht",
        "teh",
        "adn",
        "taht",
        "hte",
        "situtation",
    }
)

SUPPLEMENTARY_VALID_WORDS = frozenset(
    {
        "ai",
        "transformative",
        "paradigm",
        "stakeholders",
        "implications",
        "ethical",
        "numerous",
        "artificial",
        "intelligence",
        "deployment",
        "sectors",
        "collaborate",
        "responsible",
        "preparation",
        "grandmother",
        "english",
        "brooklyn",
        "codepath",
    }
)


@lru_cache(maxsize=1)
def _spell_checker() -> SpellChecker:
    return SpellChecker()


def _normalize_token(token: str) -> str:
    return token.lower().strip("'")


def _strip_possessive(token: str) -> str:
    lowered = token.lower()
    if lowered.endswith("'s"):
        return lowered[:-2]
    if lowered.endswith("'"):
        return lowered[:-1]
    return lowered


def _is_sentence_start(text: str, start: int) -> bool:
    prefix = text[:start]
    return not prefix or bool(re.search(r'[.!?\n]\s*$', prefix)) or start == 0


def _is_spelling_exempt(original: str, start: int, text: str) -> bool:
    normalized = _strip_possessive(_normalize_token(original))

    if not normalized or normalized.isdigit():
        return True
    if len(normalized) == 1:
        return True
    if normalized in INFORMAL_ALLOWLIST:
        return True
    if original.isupper() and 2 <= len(original) <= 6:
        return True
    if normalized in COMMON_MISSPELLINGS:
        return False
    if _is_sentence_start(text, start) and original[0].isupper():
        return False
    if original[0].isupper() and any(char.islower() for char in original[1:]):
        return True
    return False


def find_spelling_errors(text: str) -> list[str]:
    """Return deduplicated misspelled tokens found in `text`."""
    checker = _spell_checker()
    seen: set[str] = set()
    errors: list[str] = []

    for match in re.finditer(r"\b[a-zA-Z']+\b", text):
        original = match.group(0)
        if _is_spelling_exempt(original, match.start(), text):
            continue

        normalized = _strip_possessive(_normalize_token(original))
        if normalized in seen:
            continue
        seen.add(normalized)

        if normalized in COMMON_MISSPELLINGS:
            errors.append(original)
            continue
        if normalized in SUPPLEMENTARY_VALID_WORDS or normalized in checker:
            continue
        if normalized in checker.unknown([normalized]):
            errors.append(original)

    return errors


def find_grammar_issues(text: str) -> list[str]:
    """Return short descriptions of simple grammar irregularities."""
    issues: list[str] = []
    seen: set[str] = set()

    for pattern, label in GRAMMAR_PATTERNS:
        if pattern.search(text):
            if label not in seen:
                seen.add(label)
                issues.append(label)

    return issues


def find_informal_markers(text: str) -> list[str]:
    lowered = text.lower()
    return [marker for marker in INFORMAL_ALLOWLIST if re.search(rf"\b{re.escape(marker)}\b", lowered)]


def _capitalization_irregularity(text: str, sentences: list[str]) -> float:
    score = 0.0
    if any(sentence and sentence[0].islower() for sentence in sentences):
        score += 0.35
    if re.search(r"\b[A-Z]{2,}\b", text):
        score += 0.25
    return score


def _build_error_summary(
    score: float,
    spelling_errors: list[str],
    grammar_issues: list[str],
    informal_markers: list[str],
) -> str:
    if spelling_errors or grammar_issues or informal_markers:
        parts: list[str] = []
        if spelling_errors:
            sample = ", ".join(spelling_errors[:3])
            suffix = "..." if len(spelling_errors) > 3 else ""
            parts.append(f"spelling irregularities ({sample}{suffix})")
        if grammar_issues:
            parts.append("grammar issues (" + ", ".join(grammar_issues[:2]) + ")")
        if informal_markers:
            parts.append("informal markers (" + ", ".join(informal_markers[:3]) + ")")
        return "; ".join(parts)

    if score >= 0.55:
        return "polished prose with no spelling or grammar irregularities detected"
    return "limited writing-noise signals"


def analyze_error_signature(text: str) -> dict:
    """Analyze spelling/grammar noise. Higher `score` means more AI-like polish."""
    sentences = [part.strip() for part in re.split(r"[.!?]+", text) if part.strip()]
    words = re.findall(r"[a-zA-Z']+", text.lower())
    if not words:
        return {
            "score": 0.5,
            "spelling_errors": [],
            "grammar_issues": [],
            "informal_markers": [],
            "summary": "no words to analyze",
        }

    spelling_errors = find_spelling_errors(text)
    grammar_issues = find_grammar_issues(text)
    informal_markers = find_informal_markers(text)

    spelling_density = len(spelling_errors) / max(len(words), 1)
    grammar_density = len(grammar_issues) / max(len(sentences), 1)
    informal_density = len(informal_markers) / max(len(sentences), 1)
    capitalization_noise = _capitalization_irregularity(text, sentences)

    human_noise = (
        min(spelling_density * 18.0, 1.0) * 0.50
        + min(grammar_density * 2.0, 1.0) * 0.30
        + min(informal_density * 1.0, 1.0) * 0.35
        + min(capitalization_noise, 1.0) * 0.20
    )
    if len(spelling_errors) >= 3:
        human_noise += 0.12
    if len(grammar_issues) >= 2:
        human_noise += 0.12
    human_noise = min(human_noise, 1.0)
    score = max(0.0, min(1.0, 1.0 - human_noise))

    return {
        "score": score,
        "spelling_errors": spelling_errors,
        "grammar_issues": grammar_issues,
        "informal_markers": informal_markers,
        "summary": _build_error_summary(score, spelling_errors, grammar_issues, informal_markers),
    }


# --- Stylometric feature sub-scores ---

AI_TRANSITION_PHRASES = (
    "moreover",
    "it's important to note",
    "it is important to note",
    "in conclusion",
    "delve",
    "tapestry",
    "underscore",
    "boast",
    "landscape",
    "it is essential",
    "it is equally essential",
    "it is important",
    "ultimately",
    "in today's",
    "fast-paced world",
    "furthermore",
    "additionally",
    "best possible",
    "flavor profile",
    "well-being",
    "work-life balance",
    "paradigm shift",
    "transformative paradigm",
    "ethical implications",
    "responsible deployment",
    "various sectors",
    "it is equally",
)

GENERIC_FILLER = (
    "individuals", "strategies", "productivity", "overall", "essential",
    "significantly", "implementing", "achieving", "mindful", "prioritize",
    "stakeholders", "paradigm", "transformative", "collaborate", "implications",
    "numerous", "sectors", "responsible", "deployment", "benefits", "ethical",
    "society", "ensure", "consider", "represents",
)

FEATURE_WEIGHTS = {
    "burstiness": 1.0,
    "lexical diversity": 1.5,
    "punctuation regularity": 0.75,
    "structural symmetry": 0.5,
    "error signature": 1.25,
    "specificity": 1.25,
}


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _sentences(text: str) -> list[str]:
    parts = re.split(r"[.!?]+", text)
    return [part.strip() for part in parts if part.strip()]


def _words(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z']+", text.lower())


def _paragraphs(text: str) -> list[str]:
    parts = re.split(r"\n\s*\n", text.strip())
    if len(parts) == 1:
        parts = [line.strip() for line in text.splitlines() if line.strip()]
    return [part for part in parts if part]


def _linear_map(value: float, low: float, high: float) -> float:
    """Map `value` from [low, high] onto [0, 1], clamped at the ends."""
    if high <= low:
        return 0.5
    return _clamp((value - low) / (high - low))


def _burstiness_subscore(text: str) -> float:
    """Low sentence-length variance skews AI-like (higher score)."""
    sentences = _sentences(text)
    if len(sentences) < 2:
        return 0.5

    lengths = [len(_words(sentence)) for sentence in sentences]
    if not lengths or mean(lengths) == 0:
        return 0.5

    cv = pstdev(lengths) / mean(lengths) if len(lengths) > 1 else 0.0
    return _clamp(1.0 - _linear_map(cv, 0.20, 0.55))


def _lexical_diversity_subscore(text: str) -> float:
    """Low type-token ratio and common AI transition phrases skew AI-like."""
    words = _words(text)
    if len(words) < 5:
        return 0.5

    ttr = len(set(words)) / len(words)
    lowered = text.lower()
    phrase_hits = sum(1 for phrase in AI_TRANSITION_PHRASES if phrase in lowered)
    sentence_count = max(len(_sentences(text)), 1)
    phrase_density = phrase_hits / sentence_count

    ttr_score = _clamp(1.0 - _linear_map(ttr, 0.55, 0.85))
    phrase_score = _clamp(_linear_map(phrase_density, 0.25, 1.0))

    if len(words) < 80:
        return 0.25 * ttr_score + 0.75 * phrase_score
    return 0.6 * ttr_score + 0.4 * phrase_score


def _punctuation_regularity_subscore(text: str) -> float:
    """Even comma usage across sentences skews AI-like."""
    sentences = _sentences(text)
    if len(sentences) < 2:
        return 0.5

    comma_rates = [sentence.count(",") / max(len(_words(sentence)), 1) for sentence in sentences]
    if mean(comma_rates) == 0:
        return 0.35

    cv = pstdev(comma_rates) / mean(comma_rates) if len(comma_rates) > 1 else 0.0
    return _clamp(1.0 - _linear_map(cv, 0.35, 1.20))


def _structural_symmetry_subscore(text: str) -> float:
    """Even paragraph lengths and enumerated lists skew AI-like."""
    paragraphs = _paragraphs(text)
    list_lines = len(re.findall(r"^\s*(?:[-*•]|\d+[.)])\s+", text, re.MULTILINE))

    if len(paragraphs) < 2:
        paragraph_score = 0.45
    else:
        lengths = [len(_words(paragraph)) for paragraph in paragraphs]
        if mean(lengths) == 0:
            paragraph_score = 0.5
        else:
            cv = pstdev(lengths) / mean(lengths) if len(lengths) > 1 else 0.0
            paragraph_score = _clamp(1.0 - _linear_map(cv, 0.25, 0.80))

    list_score = _clamp(_linear_map(list_lines, 0, 3))
    return 0.7 * paragraph_score + 0.3 * list_score


def _error_signature_subscore(text: str) -> float:
    """Clean, error-free prose skews AI-like; real spelling/grammar noise skews human-like."""
    return analyze_error_signature(text)["score"]


def _specificity_subscore(text: str) -> float:
    """Generic filler language skews AI-like; concrete details skew human-like."""
    words = _words(text)
    if not words:
        return 0.5

    lowered = text.lower()
    generic_hits = sum(1 for phrase in GENERIC_FILLER if phrase in lowered)
    concrete_hits = len(re.findall(r"\b\d{1,4}\b", text))
    concrete_hits += len(re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+\b", text))
    concrete_hits += len(re.findall(r"\b(?:my|our|your)\s+\w+\b", lowered))

    generic_density = generic_hits / max(len(_sentences(text)), 1)
    concrete_density = concrete_hits / max(len(words), 1)

    generic_score = _clamp(_linear_map(generic_density, 0.0, 2.5))
    concrete_score = _clamp(_linear_map(concrete_density, 0.0, 0.12))
    return _clamp(0.65 * generic_score + 0.35 * (1.0 - concrete_score))


FEATURE_SUBSCORERS = (
    ("burstiness", _burstiness_subscore),
    ("lexical diversity", _lexical_diversity_subscore),
    ("punctuation regularity", _punctuation_regularity_subscore),
    ("structural symmetry", _structural_symmetry_subscore),
    ("error signature", _error_signature_subscore),
    ("specificity", _specificity_subscore),
)


def classify_stylometric(text: str) -> dict:
    """Score `text` with lightweight stylometric heuristics (no LLM call).

    Returns {"score": float in [0, 1], "explanation": str}, where score is the
    confidence that the text is AI-generated (0.0 = highly-human, 1.0 = highly-AI).
    """
    if not text or not text.strip():
        return {"score": 0.5, "explanation": "empty input; neutral stylometric score"}

    feature_scores: dict[str, float] = {}
    error_details = analyze_error_signature(text)
    for name, scorer in FEATURE_SUBSCORERS:
        if name == "error signature":
            feature_scores[name] = error_details["score"]
        else:
            feature_scores[name] = scorer(text)

    weight_total = sum(FEATURE_WEIGHTS.values())
    score = round(
        sum(feature_scores[name] * FEATURE_WEIGHTS[name] for name in feature_scores) / weight_total,
        4,
    )

    drivers = sorted(feature_scores.items(), key=lambda item: item[1], reverse=True)
    explanation_parts: list[str] = []
    for name, value in drivers[:3]:
        if name == "error signature":
            explanation_parts.append(error_details["summary"])
        elif value >= 0.55:
            explanation_parts.append(f"high {name}")
        elif value <= 0.40:
            explanation_parts.append(f"low {name}")

    if explanation_parts:
        explanation = "; ".join(explanation_parts)
    else:
        human_markers = [name for name, value in drivers if value <= 0.40]
        if human_markers:
            explanation = "more human-like " + ", ".join(human_markers[-2:])
        else:
            explanation = "mixed stylometric features; no single dominant tell"

    return {"score": _clamp(score), "explanation": explanation}
