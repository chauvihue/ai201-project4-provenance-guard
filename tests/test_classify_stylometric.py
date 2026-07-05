from stylometric_classifier_signal import classify_stylometric

HUMAN_TEXT = (
    "honestly idk how to start this but ok so yesterday my dog got into the trash AGAIN "
    "and istg he does it on purpose bcs he stares at me the whole time like daring me to stop him. "
    "anyways, i spent like 20 min cleaning it up and then found out he also chewed my charger. "
    "great. 10/10 would not recommend owning a golden retriever if you like having nice things lol"
)

AI_TEXT = (
    "In today's fast-paced world, effective time management has become more important than ever. "
    "It is essential to prioritize tasks, set clear goals, and maintain a healthy work-life balance. "
    "By implementing these strategies, individuals can significantly boost their productivity and "
    "overall well-being. Ultimately, the key to success lies in consistent effort and mindful planning."
)

MIXED_TEXT = (
    "My grandmother used to make this soup every winter, and the smell of it still takes me right "
    "back to her tiny kitchen. It is important to note that proper preparation and attention to "
    "detail are essential for achieving the best possible flavor profile. I still make it every "
    "year, though mine never tastes quite as good as hers."
)

ESL_TEXT = (
    "When I moved to this country, I found it difficult to express my ideas in English. "
    "Moreover, it is important to practice every day and to read books in English. "
    "In conclusion, learning a new language requires patience and consistent effort."
)

AI_TEXT_CODEPATH = (
    "Artificial intelligence represents a transformative paradigm shift in modern society. "
    "It is important to note that while the benefits of AI are numerous, it is equally "
    "essential to consider the ethical implications. Furthermore, stakeholders across "
    "various sectors must collaborate to ensure responsible deployment."
)


def test_stylometric_separates_clear_human_and_ai_samples():
    human = classify_stylometric(HUMAN_TEXT)
    ai = classify_stylometric(AI_TEXT)

    assert human["score"] < 0.45, f"expected low AI score for casual human text, got {human['score']}"
    assert ai["score"] > 0.55, f"expected high AI score for polished generic text, got {ai['score']}"
    assert ai["score"] - human["score"] >= 0.20


def test_stylometric_mixed_sample_lands_between_extremes():
    mixed = classify_stylometric(MIXED_TEXT)
    human = classify_stylometric(HUMAN_TEXT)
    ai = classify_stylometric(AI_TEXT)

    assert human["score"] < mixed["score"] < ai["score"]


def test_stylometric_esl_reads_more_ai_than_casual_human():
    esl = classify_stylometric(ESL_TEXT)
    human = classify_stylometric(HUMAN_TEXT)

    assert esl["score"] > human["score"]


def test_stylometric_returns_explanation():
    result = classify_stylometric(AI_TEXT)
    assert isinstance(result["explanation"], str)
    assert result["explanation"]


def test_stylometric_flags_obvious_ai_transition_prose():
    result = classify_stylometric(AI_TEXT_CODEPATH)
    assert result["score"] > 0.65, f"expected strong AI stylometric score, got {result['score']}"
