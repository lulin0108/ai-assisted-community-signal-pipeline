"""Batch processing for quality filtering and relevance preparation."""

from models import RelevanceSummary
from processors.prepare_items import prepare_items
from processors.text_quality_filter import filter_quality_items, summarize_filtering


def process_evidence_batches(raw_items: list[dict], batch_size: int) -> dict:
    candidate_items = []
    excluded_items = []
    prepared_items = []
    relevance_excluded_items = []
    batch_summaries = []

    prepared_start_index = 1
    for batch_index, start in enumerate(range(0, len(raw_items), batch_size), start=1):
        batch = raw_items[start:start + batch_size]
        batch_candidates, batch_excluded, batch_filtering_summary = filter_quality_items(batch, start_index=start + 1)
        batch_prepared, batch_relevance_excluded = prepare_items(batch_candidates, start_index=prepared_start_index)
        prepared_start_index += len(batch_candidates)

        candidate_items.extend(batch_candidates)
        excluded_items.extend(batch_excluded)
        prepared_items.extend(batch_prepared)
        relevance_excluded_items.extend(batch_relevance_excluded)
        batch_summaries.append(
            {
                "batch_index": batch_index,
                "status": "completed",
                "raw_item_start_index": start + 1,
                "raw_item_end_index": start + len(batch),
                "raw_items": len(batch),
                "quality_candidates": len(batch_candidates),
                "quality_excluded": len(batch_excluded),
                "relevance_prepared": len(batch_prepared),
                "relevance_excluded": len(batch_relevance_excluded),
                "filtering_summary": batch_filtering_summary,
            }
        )

    filtering_summary = summarize_filtering(raw_items, candidate_items, excluded_items)
    relevance_summary = RelevanceSummary(
        evidence_candidates_after_quality_filter=len(candidate_items),
        evidence_candidates_after_relevance_filter=len(prepared_items),
        relevance_filtered_items=len(relevance_excluded_items),
    ).to_dict()

    return {
        "candidate_items": candidate_items,
        "excluded_items": excluded_items,
        "filtering_summary": filtering_summary,
        "prepared_items": prepared_items,
        "relevance_excluded_items": relevance_excluded_items,
        "relevance_summary": relevance_summary,
        "batch_summaries": batch_summaries,
    }
