"""Compare LLM reference scores with stylometric signal on curated inputs."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from llm_classifier_signal import score_submission
from stylometric_classifier_signal import FEATURE_SUBSCORERS, classify_stylometric

HUMAN = (
    "honestly idk how to start this but ok so yesterday my dog got into the trash AGAIN "
    "and istg he does it on purpose bcs he stares at me the whole time like daring me to stop him. "
    "anyways, i spent like 20 min cleaning it up and then found out he also chewed my charger. "
    "great. 10/10 would not recommend owning a golden retriever if you like having nice things lol"
)

AI = (
    "In today's fast-paced world, effective time management has become more important than ever. "
    "It is essential to prioritize tasks, set clear goals, and maintain a healthy work-life balance. "
    "By implementing these strategies, individuals can significantly boost their productivity and "
    "overall well-being. Ultimately, the key to success lies in consistent effort and mindful planning."
)

MIXED = (
    "My grandmother used to make this soup every winter, and the smell of it still takes me right "
    "back to her tiny kitchen. It is important to note that proper preparation and attention to "
    "detail are essential for achieving the best possible flavor profile. I still make it every "
    "year, though mine never tastes quite as good as hers."
)

ESL = (
    "When I moved to this country, I found it difficult to express my ideas in English. "
    "Moreover, it is important to practice every day and to read books in English. "
    "In conclusion, learning a new language requires patience and consistent effort."
)

LLM_REFS = {"human": 0.05, "ai": 0.93, "mixed": 0.55, "esl": 0.45}


def band(score: float) -> str:
    if score <= 0.25:
        return "human"
    if score >= 0.80:
        return "ai"
    return "middle"


def main() -> None:
    for name, text in [("human", HUMAN), ("ai", AI), ("mixed", MIXED), ("esl", ESL)]:
        stylo = classify_stylometric(text)
        feats = {feature: round(scorer(text), 3) for feature, scorer in FEATURE_SUBSCORERS}
        llm = {"score": LLM_REFS[name], "reasoning": "planning few-shot reference"}
        combined = score_submission(llm, stylo)
        agree = band(LLM_REFS[name]) == band(stylo["score"]) or (
            band(LLM_REFS[name]) == "middle" and band(stylo["score"]) == "middle"
        )
        print(f"=== {name} ===")
        print(f"  LLM ref:      {LLM_REFS[name]:.2f}")
        print(f"  Stylometric:  {stylo['score']:.3f}  ({stylo['explanation']})")
        print(f"  Combined:     {combined['confidence']:.3f} -> {combined['label']}")
        print(f"  Agreement:    {'AGREE' if agree else 'DIVERGE'}")
        print(f"  Features:     {feats}")
        if combined["note"]:
            print("  NOTE:         yes")
        print()


if __name__ == "__main__":
    main()
