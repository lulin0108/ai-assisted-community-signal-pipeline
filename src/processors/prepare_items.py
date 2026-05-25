"""Normalize raw collector records before analysis."""

from models import PreparedItem
from processors.text_cleaner import clean_text
from processors.evidence_relevance import score_item_relevance


def prepare_items(raw_items: list[dict], start_index: int = 1) -> tuple[list[dict], list[dict]]:
    prepared = []
    relevance_excluded = []
    for index, item in enumerate(raw_items, start=start_index):
        clean = clean_text(item.get("text", ""))
        if not clean:
            continue

        item_id = f"{item.get('source_type', 'source')}-{index}"
        title = clean_text(item.get("title", ""))
        base_item = PreparedItem.from_raw(item, item_id, clean, title).to_dict()
        relevance = score_item_relevance(base_item)
        prepared_item = PreparedItem.from_raw(item, item_id, clean, title, relevance).to_dict()
        if prepared_item["exclude_for_relevance"]:
            relevance_excluded.append(prepared_item)
            continue
        prepared.append(prepared_item)
    return prepared, relevance_excluded
