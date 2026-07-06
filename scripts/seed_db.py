"""Seed logs/submissions.db with sample rows for a fresh clone.

logs/submissions.db is gitignored (it's a live, mutable SQLite file -- see
README), so a fresh clone starts empty. Run this once to get the same demo
data the repo used to ship via the old logs/audit_log.jsonl.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from audit_log import file_appeal, log_entry, update_status

SAMPLE_SUBMISSIONS = [
    {
        "content_id": "e0898037-4f8e-4834-b42c-429af3e23219",
        "creator_id": "alice",
        "submitted_at": "2026-07-05T20:09:50.522500+00:00",
        "text": (
            "honestly idk how to start this but ok so yesterday my dog got into the trash AGAIN "
            "and istg he does it on purpose bcs he stares at me the whole time. anyways i spent "
            "like 20 min cleaning it up lol"
        ),
        "label": "highly-human",
        "confidence": 0.1573,
        "note": None,
        "message": (
            "This content is **likely human-written**. Our analysis found the natural variation "
            "and irregularity typical of unassisted writing, with no strong AI fingerprint "
            "detected. Confidence: 16%. The text exhibits highly human-like characteristics, such "
            "as irregular capitalization, casual abbreviations, and a conversational tone, which "
            "suggests that it was written by a human."
        ),
        "llm_score": 0.1,
        "llm_reasoning": (
            "The text exhibits highly human-like characteristics, such as irregular "
            "capitalization, casual abbreviations, and a conversational tone, which "
            "suggests that it was written by a human."
        ),
        "stylometric_score": 0.2147,
        "stylometric_explanation": "informal markers (istg, bcs, honestly); low punctuation regularity; low structural symmetry",
        "status": "final",
    },
    {
        "content_id": "243cbc70-7470-4c7e-86b9-cf9a1e8b063f",
        "creator_id": "bob",
        "submitted_at": "2026-07-05T20:15:46.408358+00:00",
        "text": (
            "In todays fast-paced world, effective time management has become more important "
            "than ever. It is essential to prioritize tasks, set clear goals, and maintain a "
            "healthy work-life balance. By implementing these strategies, individuals can "
            "significantly boost their productivity. Ultimately, the key to success lies in "
            "consistent effort and mindful planning."
        ),
        "label": "highly-AI",
        "confidence": 0.8723,
        "note": None,
        "message": (
            "This content is **likely AI-generated**. Our analysis found strong AI fingerprints "
            "across most of the text, including a highly uniform sentence structure, generic "
            "filler phrasing, and safe hedging transitions. Confidence: 87%."
        ),
        "llm_score": 0.92,
        "llm_reasoning": (
            "The text exhibits a highly uniform sentence structure, generic filler "
            "phrasing, and safe hedging transitions, all of which are characteristic of "
            "AI-generated writing."
        ),
        "stylometric_score": 0.8246,
        "stylometric_explanation": "high burstiness; high punctuation regularity; high specificity",
        "status": "final",
    },
]

SAMPLE_APPEAL = {
    "content_id": "243cbc70-7470-4c7e-86b9-cf9a1e8b063f",
    "reasoning": (
        "I wrote this myself from personal experience. I am a non-native English speaker and my "
        "writing style may appear more formal than typical."
    ),
}


def main() -> None:
    for entry in SAMPLE_SUBMISSIONS:
        log_entry(entry)

    file_appeal(SAMPLE_APPEAL["content_id"], SAMPLE_APPEAL["reasoning"])
    update_status(SAMPLE_APPEAL["content_id"], "under_review")

    print(f"Seeded {len(SAMPLE_SUBMISSIONS)} submissions and 1 appeal into logs/submissions.db")


if __name__ == "__main__":
    main()
