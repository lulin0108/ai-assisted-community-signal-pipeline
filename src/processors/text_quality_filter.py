"""Filter raw texts before they become evidence candidates.

This module deliberately favors evidence quality over evidence quantity. It
keeps user-like discussion and review text, while excluding obvious jobs,
company self-description, product landing copy, and directory snippets.
"""

from collections import Counter

from processors.text_cleaner import clean_text, excerpt


JOB_TERMS = [
    "full-time",
    "part-time",
    "contractor",
    "product engineer",
    "software engineer",
    "apply now",
    "apply for this job",
    "job description",
    "equal opportunity employer",
    "salary range",
    "benefits",
    "careers",
    "hiring",
]

PROMOTIONAL_TERMS = [
    "book a demo",
    "request a demo",
    "sign up",
    "get started",
    "learn more",
    "our platform",
    "we help companies",
    "we empower",
    "world-class",
    "best-in-class",
    "all-in-one",
    "revolutionary",
    "seamlessly",
    "unlock",
    "trusted by",
    "transform your",
]

DIRECTORY_TERMS = [
    "company profile",
    "founded in",
    "headquartered",
    "number of employees",
    "pricing, reviews",
    "reviews and alternatives",
    "alternatives and competitors",
    "software category",
    "provider of",
    "overview of",
    "directory",
]

CONVERSATIONAL_TERMS = [
    "i ",
    "i've",
    "i'm",
    "we ",
    "we've",
    "my ",
    "our ",
    "for us",
    "for me",
    "tried",
    "using",
    "use it",
    "switched",
    "compared",
    "complain",
    "keep saying",
    "people say",
    "teams say",
    "users say",
]

QUALITY_TERMS = [
    "annoying",
    "barrier",
    "bug",
    "complain",
    "confusing",
    "crash",
    "difficult",
    "doesn't work",
    "expensive",
    "frustrating",
    "hard",
    "inaccurate",
    "issue",
    "missing",
    "need",
    "pain",
    "privacy",
    "problem",
    "setup",
    "scattered",
    "slow",
    "still need",
    "stuck",
    "too long",
    "trust",
    "workflow",
    "wrong",
]


def filter_quality_items(raw_items: list[dict]) -> tuple[list[dict], list[dict], dict]:
    kept = []
    excluded = []

    for index, item in enumerate(raw_items, start=1):
        decision = assess_item_quality(item, index)
        if decision["kept"]:
            kept_item = dict(item)
            kept_item["quality_score"] = decision["quality_score"]
            kept_item["quality_reasons"] = decision["quality_reasons"]
            kept.append(kept_item)
        else:
            excluded.append(decision)

    summary = _summarize_filtering(raw_items, kept, excluded)
    return kept, excluded, summary


def assess_item_quality(item: dict, index: int) -> dict:
    text = clean_text(item.get("text", ""))
    title = clean_text(item.get("title", ""))
    source_type = item.get("source_type", "unknown")
    combined = f"{title} {text}".lower()

    exclude_reasons = _exclusion_reasons(combined, text)
    quality_score, quality_reasons = _quality_score(item, text, combined)

    if not text:
        exclude_reasons.append("empty_text")

    if source_type == "discussion" and quality_score < 2:
        exclude_reasons.append("discussion_text_not_comment_like")

    if source_type == "review" and quality_score < 2:
        exclude_reasons.append("review_text_not_customer_feedback_like")

    kept = not exclude_reasons
    return {
        "source_index": index,
        "source_type": source_type,
        "source_name": item.get("source_name", ""),
        "source_id": item.get("source_id", ""),
        "source_url": item.get("source_url", ""),
        "title": title,
        "text_excerpt": excerpt(text, 220),
        "kept": kept,
        "quality_score": quality_score,
        "quality_reasons": "; ".join(quality_reasons),
        "exclude_reasons": "; ".join(exclude_reasons),
        "is_demo_fallback": item.get("is_demo_fallback", False),
    }


def _exclusion_reasons(combined: str, text: str) -> list[str]:
    reasons = []
    job_hits = _hits(combined, JOB_TERMS)
    promo_hits = _hits(combined, PROMOTIONAL_TERMS)
    directory_hits = _hits(combined, DIRECTORY_TERMS)

    if job_hits:
        reasons.append(f"job_or_careers_language:{', '.join(job_hits[:4])}")

    # "Remote" alone is often legitimate for app ventures, so only treat it as
    # job-like when it appears with hiring or application language.
    if "remote" in combined and any(term in combined for term in ["apply", "hiring", "job", "salary"]):
        reasons.append("job_or_careers_language:remote_with_job_context")

    if len(promo_hits) >= 2:
        reasons.append(f"promotional_or_landing_copy:{', '.join(promo_hits[:4])}")

    if directory_hits:
        reasons.append(f"directory_or_listing_snippet:{', '.join(directory_hits[:4])}")

    if _looks_like_company_self_description(text):
        reasons.append("company_self_description")

    return reasons


def _quality_score(item: dict, text: str, combined: str) -> tuple[int, list[str]]:
    source_type = item.get("source_type", "")
    score = 0
    reasons = []

    conversational_hits = _hits(f" {combined} ", CONVERSATIONAL_TERMS)
    if conversational_hits:
        score += 1
        reasons.append(f"conversational_language:{', '.join(conversational_hits[:3]).strip()}")

    quality_hits = _hits(combined, QUALITY_TERMS)
    if quality_hits:
        score += min(2, len(quality_hits))
        reasons.append(f"venture_signal_language:{', '.join(quality_hits[:5])}")

    if source_type == "review" and item.get("rating"):
        score += 1
        reasons.append("has_customer_rating")

    if source_type == "discussion" and _looks_comment_like(text):
        score += 1
        reasons.append("comment_like_length_or_style")

    if source_type == "review" and _looks_review_like(text):
        score += 1
        reasons.append("review_like_experience_statement")

    return score, "; ".join(reasons).split("; ") if reasons else ["low_user_evidence_signal"]


def _hits(text: str, terms: list[str]) -> list[str]:
    return [term for term in terms if term in text]


def _looks_like_company_self_description(text: str) -> bool:
    lowered = text.lower()
    starts_like_company = lowered.startswith(("we are ", "we're ", "our mission", "our product", "our app"))
    promotional_density = sum(1 for term in PROMOTIONAL_TERMS if term in lowered)
    first_person_customer = any(term in f" {lowered} " for term in [" i ", " my ", " for me", " tried", " using"])
    return starts_like_company and promotional_density >= 1 and not first_person_customer


def _looks_comment_like(text: str) -> bool:
    word_count = len(text.split())
    has_sentence = "." in text or "?" in text or "!" in text
    has_opinion_marker = any(
        marker in text.lower()
        for marker in ["i ", "we ", "my ", "our ", "but", "because", "keep saying", "complain"]
    )
    return 8 <= word_count <= 220 and has_sentence and has_opinion_marker


def _looks_review_like(text: str) -> bool:
    lowered = text.lower()
    word_count = len(text.split())
    has_experience = any(term in f" {lowered} " for term in [" i ", " my ", " we ", " our ", "use", "using", "tried"])
    has_feedback = any(term in lowered for term in QUALITY_TERMS)
    return 6 <= word_count <= 260 and (has_experience or has_feedback)


def _summarize_filtering(raw_items: list[dict], kept: list[dict], excluded: list[dict]) -> dict:
    raw_by_source = Counter(item.get("source_type", "unknown") for item in raw_items)
    kept_by_source = Counter(item.get("source_type", "unknown") for item in kept)
    excluded_by_source = Counter(row.get("source_type", "unknown") for row in excluded)
    reason_counts = Counter()
    for row in excluded:
        for reason in row["exclude_reasons"].split("; "):
            if reason:
                reason_counts[reason.split(":")[0]] += 1

    return {
        "raw_items_collected": len(raw_items),
        "filtered_out_items": len(excluded),
        "evidence_candidate_items": len(kept),
        "raw_by_source": dict(raw_by_source),
        "kept_by_source": dict(kept_by_source),
        "excluded_by_source": dict(excluded_by_source),
        "top_exclusion_reasons": dict(reason_counts.most_common()),
    }
