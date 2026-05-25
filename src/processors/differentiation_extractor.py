"""Extract differentiation opportunity signals."""

from processors.text_cleaner import excerpt


DIFFERENTIATION_TERMS = {
    "differentiation_opportunities": [
        "better",
        "easier",
        "automatic",
        "export",
        "search",
        "workflow",
        "integrate",
        "integration",
        "privacy",
        "accurate",
        "action items",
        "decisions",
        "follow-up",
        "custom",
        "missing",
    ],
}


def extract_differentiation_opportunities(item: dict) -> list[dict]:
    text = item.get("clean_text", "")
    lower_text = text.lower()
    signals = []

    for category, terms in DIFFERENTIATION_TERMS.items():
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

