"""Combine extracted signals into a venture-evaluation support memo."""

from collections import Counter, defaultdict
from datetime import datetime, timezone

from processors.adoption_barrier_extractor import extract_adoption_barriers
from processors.differentiation_extractor import extract_differentiation_opportunities
from processors.evidence_relevance import score_signal_relevance, should_keep_signal
from processors.problem_signal_extractor import extract_problem_signals


CATEGORY_TITLES = {
    "recurring_problem_signals": "Recurring operational pain signals",
    "unmet_needs": "Unmet needs",
    "adoption_barriers": "Adoption barriers",
    "dissatisfaction_current_solutions": "Dissatisfaction with current solutions",
    "differentiation_opportunities": "Differentiation opportunities",
    "community_traction_clues": "Community traction clues / demand clues",
    "competing_solution_mentions": "Competing solution mentions",
}


def analyze_venture_signals(items: list[dict], config, run_id: str) -> dict:
    evidence_rows = []

    for item in items:
        signals = []
        signals.extend(extract_problem_signals(item))
        signals.extend(extract_adoption_barriers(item))
        signals.extend(extract_differentiation_opportunities(item))

        for signal in signals:
            row = {
                "run_id": run_id,
                "category": signal["category"],
                "category_title": CATEGORY_TITLES.get(signal["category"], signal["category"]),
                "matched_terms": signal["matched_terms"],
                "evidence_excerpt": signal["evidence_excerpt"],
                "item_id": item["item_id"],
                "source_type": item["source_type"],
                "source_name": item["source_name"],
                "source_url": item["source_url"],
                "title": item["title"],
                "created_at": item["created_at"],
                "rating": item.get("rating", ""),
                "quality_score": item.get("quality_score", ""),
                "quality_reasons": item.get("quality_reasons", ""),
                "relevance_score": item.get("relevance_score", ""),
                "signal_relevance_score": 0,
                "relevance_reasons": item.get("relevance_reasons", ""),
                "relevance_penalties": item.get("relevance_penalties", ""),
                "is_demo_fallback": item.get("is_demo_fallback", False),
                "fallback_label": item.get("fallback_label", ""),
                "fallback_reason": item.get("fallback_reason", ""),
            }
            row["signal_relevance_score"] = score_signal_relevance(row)
            if should_keep_signal(row):
                evidence_rows.append(row)

    evidence_rows = sorted(evidence_rows, key=lambda row: row["signal_relevance_score"], reverse=True)
    summaries = _build_category_summaries(evidence_rows)
    source_counts = Counter(item["source_type"] for item in items)
    fallback_count = sum(1 for item in items if item.get("is_demo_fallback"))

    return {
        "run_metadata": {
            "run_id": run_id,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "project_title": config.project_title,
            "venture_category": config.product_theme,
            "community_query": config.community_query,
            "community_queries": config.community_queries,
            "stackexchange_site": config.stackexchange_site,
            "stackexchange_query": config.stackexchange_query,
            "stackexchange_queries": config.stackexchange_queries,
        },
        "data_sources": [
            {
                "source_type": "discussion",
                "source_name": "Hacker News Algolia comments",
                "role": "Early market conversation, operational pain articulation, unmet needs, and community demand clues.",
            },
            {
                "source_type": "review",
                "source_name": "Stack Overflow public questions",
                "role": "Setup friction, onboarding pain, integration problems, implementation barriers, practical constraints, and dissatisfaction with current tools.",
            },
        ],
        "volume": {
            "total_items_analyzed": len(items),
            "discussion_items": source_counts.get("discussion", 0),
            "review_items": source_counts.get("review", 0),
            "evidence_rows": len(evidence_rows),
            "demo_fallback_items": fallback_count,
        },
        "category_summaries": summaries,
        "evidence_rows": evidence_rows,
        "uncertainty_notes": _uncertainty_notes(items, evidence_rows, fallback_count),
        "venture_implications": _venture_implications(summaries),
        "limitations": [
            "This memo is supplementary evidence for human review, not an investment recommendation.",
            "Public online comments and issue feedback are noisy, incomplete, and selection-biased.",
            "The MVP uses transparent heuristics rather than trained classifiers or validated causal models.",
            "Source coverage is intentionally narrow for demo reliability.",
            "Evidence snippets should be checked in source context before any consequential decision.",
        ],
    }


def _build_category_summaries(evidence_rows: list[dict]) -> dict:
    grouped = defaultdict(list)
    for row in evidence_rows:
        grouped[row["category"]].append(row)

    summaries = {}
    for category, title in CATEGORY_TITLES.items():
        rows = grouped.get(category, [])
        rows = sorted(rows, key=lambda row: row["signal_relevance_score"], reverse=True)
        term_counter = Counter()
        source_counter = Counter()
        for row in rows:
            source_counter[row["source_type"]] += 1
            for term in row["matched_terms"].split(", "):
                if term:
                    term_counter[term] += 1

        if rows:
            summary_text = (
                f"Found {len(rows)} evidence item(s). Common indicators: "
                f"{', '.join(term for term, _ in term_counter.most_common(5))}."
            )
        else:
            summary_text = "No strong heuristic evidence found in this run."

        summaries[category] = {
            "title": title,
            "evidence_count": len(rows),
            "discussion_count": source_counter.get("discussion", 0),
            "review_count": source_counter.get("review", 0),
            "top_terms": [term for term, _ in term_counter.most_common(5)],
            "summary": summary_text,
            "example_evidence": [row["evidence_excerpt"] for row in rows[:3]],
            "example_scores": [row["signal_relevance_score"] for row in rows[:3]],
        }

    return summaries


def _uncertainty_notes(items: list[dict], evidence_rows: list[dict], fallback_count: int) -> list[str]:
    notes = [
        "The evidence is directional and should be treated as weak-signal input for diligence questions.",
        "A higher evidence count means more heuristic matches, not higher investment quality.",
    ]
    if fallback_count:
        notes.append(
            f"{fallback_count} item(s) came from built-in fallback records because one or more live public endpoints were unavailable."
        )
    if len(items) < 10:
        notes.append("The analyzed sample is small; results are useful for demo framing but not market validation.")
    if not evidence_rows:
        notes.append("No heuristic evidence rows were extracted; expand the query or source coverage before interpreting results.")
    return notes


def _venture_implications(summaries: dict) -> list[str]:
    implications = []
    if summaries["recurring_problem_signals"]["evidence_count"]:
        implications.append("Recurring operational-pain language can help shape diligence questions around pain intensity, workflow frequency, and buyer urgency.")
    if summaries["unmet_needs"]["evidence_count"]:
        implications.append("Unmet-need evidence may indicate spaces where current solutions are incomplete or poorly matched to user expectations.")
    if summaries["adoption_barriers"]["evidence_count"]:
        implications.append("Adoption barriers should be tested directly because friction can limit traction even when demand exists.")
    if summaries["differentiation_opportunities"]["evidence_count"]:
        implications.append("Differentiation clues can inform product wedge hypotheses and competitive positioning questions.")
    if summaries["competing_solution_mentions"]["evidence_count"]:
        implications.append("Competitor mentions suggest the evaluator should map alternatives, switching costs, and perceived gaps.")
    if not implications:
        implications.append("This run did not surface enough evidence to support strong venture-evaluation implications.")
    return implications
