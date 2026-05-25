"""Project configuration.

Configuration supports four levels, in priority order:

1. Command-line arguments.
2. JSON config files.
3. Environment variables.
4. Built-in defaults.
"""

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import os
from typing import Any


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

DEFAULT_EMBEDDING_BACKEND = "hashing"
DEFAULT_EMBEDDING_MODEL = ""
DEFAULT_CLUSTER_SIMILARITY_THRESHOLD = 0.12


def _get_int(name: str, default: int) -> int:
    value = os.getenv(name)
    return _parse_int(value, default)


def _parse_int(value: str | int | None, default: int) -> int:
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _parse_float(value: str | float | None, default: float) -> float:
    if not value:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    return _parse_bool(value, default)


def _parse_bool(value: str | bool | None, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _get_list(name: str, default: list[str]) -> list[str]:
    value = os.getenv(name)
    return _parse_list(value, default)


def _parse_list(value: str | list[str] | None, default: list[str]) -> list[str]:
    if not value:
        return default
    if isinstance(value, list):
        return value or default
    items = [item.strip() for item in value.split(";") if item.strip()]
    return items or default


def _config_value(values: dict[str, Any], *names: str) -> Any:
    for name in names:
        if name in values:
            return values[name]
    return None


def _load_config_file(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Config file must contain a JSON object.")
    return data


def _first_text(cli_value: str | None, config_value: Any, env_name: str, default: str) -> str:
    if cli_value:
        return cli_value
    if config_value:
        return str(config_value)
    return os.getenv(env_name, default)


def _first_int(args: argparse.Namespace, config_values: dict[str, Any], cli_name: str, config_name: str, env_name: str, default: int) -> int:
    return _parse_int(
        getattr(args, cli_name, None),
        _parse_int(_config_value(config_values, config_name), _get_int(env_name, default)),
    )


def _first_bool(args: argparse.Namespace, config_values: dict[str, Any], cli_name: str, config_name: str, env_name: str, default: bool) -> bool:
    return _parse_bool(
        getattr(args, cli_name, None),
        _parse_bool(_config_value(config_values, config_name), _get_bool(env_name, default)),
    )


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
    processing_batch_size: int
    embedding_backend: str
    embedding_model: str
    cluster_similarity_threshold: float
    enable_discussion_source: bool
    enable_review_source: bool
    discussion_page_size: int
    discussion_max_pages_per_query: int
    discussion_sort: str
    review_page_size: int
    review_max_pages_per_query: int
    review_sort: str
    review_order: str
    debug_save_raw: bool
    raw_items_file: str
    resume_from_run_id: str
    root_dir: Path
    raw_dir: Path
    processed_dir: Path
    storage_dir: Path
    sqlite_path: Path
    csv_dir: Path
    markdown_dir: Path
    html_dir: Path

    @classmethod
    def from_env(cls) -> "PipelineConfig":
        return cls._build()

    @classmethod
    def from_args(cls, argv: list[str] | None = None) -> "PipelineConfig":
        args = build_arg_parser().parse_args(argv)
        return cls._build(args)

    @classmethod
    def _build(cls, args: argparse.Namespace | None = None) -> "PipelineConfig":
        args = args or argparse.Namespace()
        config_values = _load_config_file(getattr(args, "config", None))
        env_community_queries = _get_list("COMMUNITY_QUERIES", DEFAULT_COMMUNITY_QUERIES)
        env_stackexchange_queries = _get_list("STACKEXCHANGE_QUERIES", DEFAULT_STACKEXCHANGE_QUERIES)
        product_theme = os.getenv(
            "PRODUCT_THEME",
            DEFAULT_VENTURE_CATEGORY,
        )
        product_theme = getattr(args, "theme", None) or _config_value(config_values, "theme", "product_theme") or product_theme
        community_queries = _parse_list(
            getattr(args, "community_queries", None),
            _parse_list(_config_value(config_values, "community_queries"), env_community_queries),
        )
        stackexchange_queries = _parse_list(
            getattr(args, "stackexchange_queries", None),
            _parse_list(_config_value(config_values, "stackexchange_queries"), env_stackexchange_queries),
        )
        max_discussion_items = _parse_int(
            getattr(args, "max_discussion_items", None),
            _parse_int(_config_value(config_values, "max_discussion_items"), _get_int("MAX_DISCUSSION_ITEMS", 50)),
        )
        max_review_items = _parse_int(
            getattr(args, "max_review_items", None),
            _parse_int(_config_value(config_values, "max_review_items"), _get_int("MAX_REVIEW_ITEMS", 50)),
        )
        request_timeout = _parse_int(
            getattr(args, "request_timeout", None),
            _parse_int(_config_value(config_values, "request_timeout"), _get_int("REQUEST_TIMEOUT", 25)),
        )
        processing_batch_size = _parse_int(
            getattr(args, "processing_batch_size", None),
            _parse_int(_config_value(config_values, "processing_batch_size"), _get_int("PROCESSING_BATCH_SIZE", 500)),
        )
        embedding_backend = _first_text(
            getattr(args, "embedding_backend", None),
            _config_value(config_values, "embedding_backend"),
            "EMBEDDING_BACKEND",
            DEFAULT_EMBEDDING_BACKEND,
        )
        embedding_model = _first_text(
            getattr(args, "embedding_model", None),
            _config_value(config_values, "embedding_model"),
            "EMBEDDING_MODEL",
            DEFAULT_EMBEDDING_MODEL,
        )
        cluster_similarity_threshold = _parse_float(
            getattr(args, "cluster_similarity_threshold", None),
            _parse_float(
                _config_value(config_values, "cluster_similarity_threshold"),
                _parse_float(os.getenv("CLUSTER_SIMILARITY_THRESHOLD"), DEFAULT_CLUSTER_SIMILARITY_THRESHOLD),
            ),
        )
        enable_discussion_source = _first_bool(args, config_values, "enable_discussion_source", "enable_discussion_source", "ENABLE_DISCUSSION_SOURCE", True)
        enable_review_source = _first_bool(args, config_values, "enable_review_source", "enable_review_source", "ENABLE_REVIEW_SOURCE", True)
        discussion_page_size = _first_int(args, config_values, "discussion_page_size", "discussion_page_size", "DISCUSSION_PAGE_SIZE", 0)
        discussion_max_pages_per_query = _first_int(args, config_values, "discussion_max_pages_per_query", "discussion_max_pages_per_query", "DISCUSSION_MAX_PAGES_PER_QUERY", 0)
        discussion_sort = _first_text(
            getattr(args, "discussion_sort", None),
            _config_value(config_values, "discussion_sort"),
            "DISCUSSION_SORT",
            "relevance",
        )
        review_page_size = _first_int(args, config_values, "review_page_size", "review_page_size", "REVIEW_PAGE_SIZE", 0)
        review_max_pages_per_query = _first_int(args, config_values, "review_max_pages_per_query", "review_max_pages_per_query", "REVIEW_MAX_PAGES_PER_QUERY", 0)
        review_sort = _first_text(
            getattr(args, "review_sort", None),
            _config_value(config_values, "review_sort"),
            "REVIEW_SORT",
            "activity",
        )
        review_order = _first_text(
            getattr(args, "review_order", None),
            _config_value(config_values, "review_order"),
            "REVIEW_ORDER",
            "desc",
        )
        debug_save_raw = _parse_bool(
            getattr(args, "debug_save_raw", None),
            _parse_bool(_config_value(config_values, "debug_save_raw"), _get_bool("DEBUG_SAVE_RAW", True)),
        )
        raw_items_file = _first_text(
            getattr(args, "raw_items_file", None),
            _config_value(config_values, "raw_items_file"),
            "RAW_ITEMS_FILE",
            "",
        )
        resume_from_run_id = _first_text(
            getattr(args, "resume_from_run_id", None),
            _config_value(config_values, "resume_from_run_id"),
            "RESUME_FROM_RUN_ID",
            "",
        )
        return cls(
            project_title="AI-Assisted Community Signal Pipeline for Early-Stage Venture Evaluation",
            product_theme=product_theme,
            community_query=_first_text(
                getattr(args, "community_query", None),
                _config_value(config_values, "community_query"),
                "COMMUNITY_QUERY",
                community_queries[0],
            ),
            community_queries=community_queries,
            stackexchange_site=_first_text(
                getattr(args, "stackexchange_site", None),
                _config_value(config_values, "stackexchange_site"),
                "STACKEXCHANGE_SITE",
                "stackoverflow",
            ),
            stackexchange_query=_first_text(
                getattr(args, "stackexchange_query", None),
                _config_value(config_values, "stackexchange_query"),
                "STACKEXCHANGE_QUERY",
                stackexchange_queries[0],
            ),
            stackexchange_queries=stackexchange_queries,
            max_discussion_items=max_discussion_items,
            max_review_items=max_review_items,
            request_timeout=request_timeout,
            processing_batch_size=processing_batch_size,
            embedding_backend=embedding_backend,
            embedding_model=embedding_model,
            cluster_similarity_threshold=cluster_similarity_threshold,
            enable_discussion_source=enable_discussion_source,
            enable_review_source=enable_review_source,
            discussion_page_size=discussion_page_size,
            discussion_max_pages_per_query=discussion_max_pages_per_query,
            discussion_sort=discussion_sort,
            review_page_size=review_page_size,
            review_max_pages_per_query=review_max_pages_per_query,
            review_sort=review_sort,
            review_order=review_order,
            debug_save_raw=debug_save_raw,
            raw_items_file=raw_items_file,
            resume_from_run_id=resume_from_run_id,
            root_dir=ROOT_DIR,
            raw_dir=ROOT_DIR / "data" / "raw",
            processed_dir=ROOT_DIR / "data" / "processed",
            storage_dir=ROOT_DIR / "data" / "storage",
            sqlite_path=ROOT_DIR / "data" / "storage" / "pipeline_runs.sqlite3",
            csv_dir=ROOT_DIR / "output" / "csv",
            markdown_dir=ROOT_DIR / "output" / "md",
            html_dir=ROOT_DIR / "output" / "html",
        )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the AI-assisted community signal pipeline.",
    )
    parser.add_argument(
        "--config",
        help="Path to a JSON run configuration file.",
    )
    parser.add_argument(
        "--theme",
        help="Venture category or product theme to analyze.",
    )
    parser.add_argument(
        "--community-query",
        help="Primary public discussion query label for report metadata.",
    )
    parser.add_argument(
        "--community-queries",
        help="Semicolon-separated Hacker News query family.",
    )
    parser.add_argument(
        "--stackexchange-site",
        help="Stack Exchange site to query, such as stackoverflow.",
    )
    parser.add_argument(
        "--stackexchange-query",
        help="Primary Stack Exchange query label for report metadata.",
    )
    parser.add_argument(
        "--stackexchange-queries",
        help="Semicolon-separated Stack Exchange query family.",
    )
    parser.add_argument(
        "--max-discussion-items",
        type=int,
        help="Maximum Hacker News discussion items to collect.",
    )
    parser.add_argument(
        "--max-review-items",
        type=int,
        help="Maximum Stack Exchange question items to collect.",
    )
    parser.add_argument(
        "--request-timeout",
        type=int,
        help="HTTP request timeout in seconds.",
    )
    parser.add_argument(
        "--processing-batch-size",
        type=int,
        help="Number of raw items to process per filtering and relevance batch.",
    )
    parser.add_argument(
        "--embedding-backend",
        choices=["hashing", "sentence-transformer"],
        help="Embedding backend for embedding artifacts and cluster similarity.",
    )
    parser.add_argument(
        "--embedding-model",
        help="Local sentence-transformer model identifier when using --embedding-backend sentence-transformer.",
    )
    parser.add_argument(
        "--cluster-similarity-threshold",
        type=float,
        help="Cosine similarity threshold for splitting items inside each pain-mechanism bucket.",
    )
    discussion_group = parser.add_mutually_exclusive_group()
    discussion_group.add_argument(
        "--enable-discussion-source",
        action="store_true",
        default=None,
        help="Enable Hacker News discussion collection.",
    )
    discussion_group.add_argument(
        "--disable-discussion-source",
        action="store_false",
        dest="enable_discussion_source",
        default=None,
        help="Disable Hacker News discussion collection.",
    )
    review_group = parser.add_mutually_exclusive_group()
    review_group.add_argument(
        "--enable-review-source",
        action="store_true",
        default=None,
        help="Enable Stack Exchange review/feedback collection.",
    )
    review_group.add_argument(
        "--disable-review-source",
        action="store_false",
        dest="enable_review_source",
        default=None,
        help="Disable Stack Exchange review/feedback collection.",
    )
    parser.add_argument(
        "--discussion-page-size",
        type=int,
        help="Hacker News items requested per API page. Use 0 for automatic sizing.",
    )
    parser.add_argument(
        "--discussion-max-pages-per-query",
        type=int,
        help="Maximum Hacker News pages to request per query. Use 0 for automatic depth.",
    )
    parser.add_argument(
        "--discussion-sort",
        choices=["relevance", "date"],
        help="Hacker News Algolia search order.",
    )
    parser.add_argument(
        "--review-page-size",
        type=int,
        help="Stack Exchange items requested per API page. Use 0 for automatic sizing.",
    )
    parser.add_argument(
        "--review-max-pages-per-query",
        type=int,
        help="Maximum Stack Exchange pages to request per query. Use 0 for automatic depth.",
    )
    parser.add_argument(
        "--review-sort",
        choices=["activity", "creation", "votes", "relevance"],
        help="Stack Exchange sort field.",
    )
    parser.add_argument(
        "--review-order",
        choices=["desc", "asc"],
        help="Stack Exchange sort order.",
    )
    parser.add_argument(
        "--raw-items-file",
        help="Path to a local JSON list of raw items. Skips live collectors.",
    )
    parser.add_argument(
        "--resume-from-run-id",
        help="Resume live collection from stored collection state for a previous run ID.",
    )
    debug_group = parser.add_mutually_exclusive_group()
    debug_group.add_argument(
        "--debug-save-raw",
        action="store_true",
        default=None,
        help="Save latest raw API responses for debugging.",
    )
    debug_group.add_argument(
        "--no-debug-save-raw",
        action="store_false",
        dest="debug_save_raw",
        default=None,
        help="Do not save latest raw API responses.",
    )
    return parser
