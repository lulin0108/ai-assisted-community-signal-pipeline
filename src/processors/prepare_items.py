"""Normalize raw collector records before analysis."""

from processors.text_cleaner import clean_text
from processors.evidence_relevance import score_item_relevance


def prepare_items(raw_items: list[dict]) -> tuple[list[dict], list[dict]]:
    prepared = []
    relevance_excluded = []
    for index, item in enumerate(raw_items, start=1):
        clean = clean_text(item.get("text", ""))
        if not clean:
            continue

        prepared_item = {
                "item_id": f"{item.get('source_type', 'source')}-{index}",
                "source_type": item.get("source_type", ""),
                "source_name": item.get("source_name", ""),
                "source_id": item.get("source_id", ""),
                "source_url": item.get("source_url", ""),
                "title": clean_text(item.get("title", "")),
                "author": item.get("author", ""),
                "created_at": item.get("created_at", ""),
                "collected_at": item.get("collected_at", ""),
                "product_theme": item.get("product_theme", ""),
                "query_theme": item.get("query_theme", ""),
                "reviewed_product": item.get("reviewed_product", ""),
                "rating": item.get("rating", ""),
                "clean_text": clean,
                "quality_score": item.get("quality_score", ""),
                "quality_reasons": item.get("quality_reasons", ""),
                "is_demo_fallback": item.get("is_demo_fallback", False),
                "fallback_label": item.get("fallback_label", ""),
                "fallback_reason": item.get("fallback_reason", ""),
            }
        relevance = score_item_relevance(prepared_item)
        prepared_item.update(relevance)
        if prepared_item["exclude_for_relevance"]:
            relevance_excluded.append(prepared_item)
            continue
        prepared.append(prepared_item)
    return prepared, relevance_excluded
