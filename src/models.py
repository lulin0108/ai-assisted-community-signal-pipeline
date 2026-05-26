"""Shared data contracts for pipeline records."""

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class RawItem:
    source_type: str
    source_name: str
    source_id: str
    source_url: str
    title: str
    author: str
    created_at: str
    collected_at: str
    product_theme: str
    query_theme: str
    text: str
    reviewed_product: str = ""
    rating: str = ""
    is_demo_fallback: bool = False
    fallback_label: str = ""
    fallback_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CollectorDiagnostics:
    source: str
    endpoint: str
    expected_response_format: str
    live_items_fetched_count: int = 0
    fallback_triggered: bool | None = None
    fallback_reason: str = ""
    failure_type: str = ""
    fallback_items_inserted: int = 0
    debug_raw_file: str = ""
    query_used: list[str] = field(default_factory=list)
    request_urls: list[str] = field(default_factory=list)
    stackexchange_site: str = ""
    stackexchange_query: list[str] = field(default_factory=list)
    request_params: list[dict[str, Any]] = field(default_factory=list)
    collected_pages: list[dict[str, Any]] = field(default_factory=list)
    live_question_count_fetched: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CollectedPage:
    source: str
    query: str
    page_number: int
    items: list[dict[str, Any]]
    raw_count: int
    has_more: bool
    request_url: str = ""
    request_params: dict[str, Any] = field(default_factory=dict)
    raw_response: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CollectionState:
    source: str
    query: str
    page_count: int
    last_page_number: int
    next_page_number: int
    total_raw_count: int
    total_item_count: int
    completed: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FilteringSummary:
    raw_items_collected: int
    filtered_out_items: int
    evidence_candidate_items: int
    raw_by_source: dict[str, int]
    kept_by_source: dict[str, int]
    excluded_by_source: dict[str, int]
    top_exclusion_reasons: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RelevanceSummary:
    evidence_candidates_after_quality_filter: int
    evidence_candidates_after_relevance_filter: int
    relevance_filtered_items: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RunMetadata:
    run_id: str
    generated_at_utc: str
    project_title: str
    venture_category: str
    community_query: str
    community_queries: list[str]
    stackexchange_site: str
    stackexchange_query: str
    stackexchange_queries: list[str]
    max_discussion_items: int
    max_review_items: int
    request_timeout: int
    processing_batch_size: int
    collection_policy: dict[str, Any]
    debug_save_raw: bool
    raw_items_file: str
    resume_from_run_id: str = ""
    embedding_policy: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class VolumeSummary:
    total_items_analyzed: int
    discussion_items: int
    review_items: int
    evidence_rows: int
    demo_fallback_items: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AnalysisResult:
    run_metadata: dict[str, Any]
    data_sources: list[dict[str, str]]
    volume: dict[str, int]
    category_summaries: dict[str, dict[str, Any]]
    evidence_rows: list[dict[str, Any]]
    uncertainty_notes: list[str]
    venture_implications: list[str]
    limitations: list[str]
    filtering_summary: dict[str, Any]
    relevance_summary: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PreparedItem:
    item_id: str
    source_type: str
    source_name: str
    source_id: str
    source_url: str
    title: str
    author: str
    created_at: str
    collected_at: str
    product_theme: str
    query_theme: str
    reviewed_product: str
    rating: str
    clean_text: str
    quality_score: int | str = ""
    quality_reasons: str = ""
    relevance_score: int = 0
    relevance_reasons: str = ""
    relevance_penalties: str = ""
    exclude_for_relevance: bool = False
    is_demo_fallback: bool = False
    fallback_label: str = ""
    fallback_reason: str = ""

    @classmethod
    def from_raw(
        cls,
        raw_item: dict[str, Any],
        item_id: str,
        clean_text: str,
        title: str,
        relevance: dict[str, Any] | None = None,
    ) -> "PreparedItem":
        relevance = relevance or {}
        return cls(
            item_id=item_id,
            source_type=raw_item.get("source_type", ""),
            source_name=raw_item.get("source_name", ""),
            source_id=raw_item.get("source_id", ""),
            source_url=raw_item.get("source_url", ""),
            title=title,
            author=raw_item.get("author", ""),
            created_at=raw_item.get("created_at", ""),
            collected_at=raw_item.get("collected_at", ""),
            product_theme=raw_item.get("product_theme", ""),
            query_theme=raw_item.get("query_theme", ""),
            reviewed_product=raw_item.get("reviewed_product", ""),
            rating=raw_item.get("rating", ""),
            clean_text=clean_text,
            quality_score=raw_item.get("quality_score", ""),
            quality_reasons=raw_item.get("quality_reasons", ""),
            relevance_score=relevance.get("relevance_score", 0),
            relevance_reasons=relevance.get("relevance_reasons", ""),
            relevance_penalties=relevance.get("relevance_penalties", ""),
            exclude_for_relevance=relevance.get("exclude_for_relevance", False),
            is_demo_fallback=raw_item.get("is_demo_fallback", False),
            fallback_label=raw_item.get("fallback_label", ""),
            fallback_reason=raw_item.get("fallback_reason", ""),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EvidenceRow:
    run_id: str
    category: str
    category_title: str
    matched_terms: str
    evidence_excerpt: str
    item_id: str
    source_type: str
    source_name: str
    source_id: str
    source_url: str
    title: str
    created_at: str
    rating: str
    quality_score: int | str
    quality_reasons: str
    relevance_score: int | str
    signal_relevance_score: int
    relevance_reasons: str
    relevance_penalties: str
    is_demo_fallback: bool
    fallback_label: str
    fallback_reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
