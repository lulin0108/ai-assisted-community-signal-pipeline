"""Project configuration.

The MVP uses environment variables so the demo can run without extra packages.
"""

from dataclasses import dataclass
from pathlib import Path
import os


ROOT_DIR = Path(__file__).resolve().parents[1]

DEFAULT_VENTURE_CATEGORY = "AI-enabled tools for small-business operations, lean teams, and one-person companies"

DEFAULT_COMMUNITY_QUERIES = [
    "small business workflow pain",
    "admin automation frustration",
    "CRM frustration small business",
    "solo founder automation",
]

DEFAULT_STACKEXCHANGE_QUERIES = [
    "workflow automation integration",
    "crm api integration problem",
    "zapier automation error",
    "n8n setup issue",
]


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _get_list(name: str, default: list[str]) -> list[str]:
    value = os.getenv(name)
    if not value:
        return default
    items = [item.strip() for item in value.split(";") if item.strip()]
    return items or default


@dataclass(frozen=True)
class PipelineConfig:
    project_title: str
    product_theme: str
    community_query: str
    community_queries: list[str]
    stackexchange_site: str
    stackexchange_query: str
    stackexchange_queries: list[str]
    max_discussion_items: int
    max_review_items: int
    request_timeout: int
    debug_save_raw: bool
    root_dir: Path
    raw_dir: Path
    processed_dir: Path
    csv_dir: Path
    markdown_dir: Path
    html_dir: Path

    @classmethod
    def from_env(cls) -> "PipelineConfig":
        product_theme = os.getenv(
            "PRODUCT_THEME",
            DEFAULT_VENTURE_CATEGORY,
        )
        community_queries = _get_list("COMMUNITY_QUERIES", DEFAULT_COMMUNITY_QUERIES)
        stackexchange_queries = _get_list("STACKEXCHANGE_QUERIES", DEFAULT_STACKEXCHANGE_QUERIES)
        return cls(
            project_title="AI-Assisted Community Signal Pipeline for Early-Stage Venture Evaluation",
            product_theme=product_theme,
            community_query=os.getenv("COMMUNITY_QUERY", community_queries[0]),
            community_queries=community_queries,
            stackexchange_site=os.getenv("STACKEXCHANGE_SITE", "stackoverflow"),
            stackexchange_query=os.getenv("STACKEXCHANGE_QUERY", stackexchange_queries[0]),
            stackexchange_queries=stackexchange_queries,
            max_discussion_items=_get_int("MAX_DISCUSSION_ITEMS", 50),
            max_review_items=_get_int("MAX_REVIEW_ITEMS", 50),
            request_timeout=_get_int("REQUEST_TIMEOUT", 25),
            debug_save_raw=_get_bool("DEBUG_SAVE_RAW", True),
            root_dir=ROOT_DIR,
            raw_dir=ROOT_DIR / "data" / "raw",
            processed_dir=ROOT_DIR / "data" / "processed",
            csv_dir=ROOT_DIR / "output" / "csv",
            markdown_dir=ROOT_DIR / "output" / "md",
            html_dir=ROOT_DIR / "output" / "html",
        )
