"""Extract problem, unmet need, demand, and competitor signals."""

from processors.text_cleaner import excerpt


SIGNAL_TERMS = {
    "recurring_problem_signals": [
        "problem",
        "pain",
        "hard",
        "difficult",
        "frustrating",
        "annoying",
        "manual",
        "waste",
        "scattered",
        "slow",
        "broken",
        "missing",
    ],
    "unmet_needs": [
        "need",
        "wish",
        "want",
        "looking for",
        "would pay",
        "if only",
        "missing",
        "should support",
        "doesn't support",
    ],
    "community_traction_clues": [
        "using",
        "tried",
        "recommend",
        "switched",
        "adopted",
        "team",
        "customers",
        "demand",
        "popular",
        "save time",
    ],
    "competing_solution_mentions": [
        "notion",
        "slack",
        "google",
        "microsoft",
        "zoom",
        "teams",
        "linear",
        "jira",
        "asana",
        "todoist",
        "obsidian",
    ],
}


def extract_problem_signals(item: dict) -> list[dict]:
    return _extract(item, SIGNAL_TERMS)


def _extract(item: dict, groups: dict[str, list[str]]) -> list[dict]:
    text = item.get("clean_text", "")
    lower_text = text.lower()
    signals = []

    for category, terms in groups.items():
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

