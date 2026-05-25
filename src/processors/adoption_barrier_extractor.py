"""Extract adoption barriers and dissatisfaction signals."""

from processors.text_cleaner import excerpt


BARRIER_TERMS = {
    "adoption_barriers": [
        "setup",
        "integration",
        "permission",
        "privacy",
        "security",
        "expensive",
        "price",
        "cost",
        "learning curve",
        "workflow",
        "trust",
        "accuracy",
        "too long",
        "hard to use",
    ],
    "dissatisfaction_current_solutions": [
        "bug",
        "crash",
        "slow",
        "wrong",
        "inaccurate",
        "doesn't work",
        "not useful",
        "still need",
        "manual cleanup",
        "missing",
        "frustrating",
    ],
}


def extract_adoption_barriers(item: dict) -> list[dict]:
    text = item.get("clean_text", "")
    lower_text = text.lower()
    signals = []

    for category, terms in BARRIER_TERMS.items():
        matched_terms = [term for term in terms if term in lower_text]
        if matched_terms:
            signals.append(
                {
                    "category": category,
                    "matched_terms": ", ".join(matched_terms[:6]),
                    "evidence_excerpt": excerpt(text),
                }
            )
    return signals

