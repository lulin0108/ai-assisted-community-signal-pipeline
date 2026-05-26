"""Collector for Source Type 1: public discussion/community data.

The MVP uses Hacker News comments through the public Algolia API.
"""

from datetime import datetime, timezone
from json import JSONDecodeError
from math import ceil
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import json
import logging
import socket
import time

from models import CollectedPage, CollectorDiagnostics, RawItem


HN_SEARCH_ENDPOINT = "https://hn.algolia.com/api/v1/search"
HN_SEARCH_BY_DATE_ENDPOINT = "https://hn.algolia.com/api/v1/search_by_date"
COLLECTOR_FAILURES = (HTTPError, URLError, TimeoutError, socket.timeout, JSONDecodeError, ValueError)
logger = logging.getLogger(__name__)


def collect_discussion_items(config, start_pages: dict[str, int] | None = None) -> tuple[list[dict], dict]:
    queries = _queries_to_collect(config.community_queries, start_pages)
    diagnostics = _base_diagnostics(config, queries)
    diagnostics["resume_start_pages"] = start_pages or {}

    logger.info("[Source 1] Public discussion/community source")
    logger.info("[Source 1] Endpoint: %s", _search_endpoint(config))
    logger.info("[Source 1] Query family: %s", queries)
    if start_pages is not None:
        logger.info("[Source 1] Resume start pages: %s", start_pages)
    logger.info("[Source 1] Expected response: JSON object with a 'hits' list of Hacker News comment records.")

    try:
        items = []
        seen_ids = set()
        debug_responses = []

        if not queries:
            diagnostics["fallback_triggered"] = False
            return [], diagnostics

        for page in iter_discussion_pages(config, start_pages):
            diagnostics["request_urls"].append(page["request_url"])
            diagnostics["collected_pages"].append(_page_diagnostic(page))
            debug_responses.append(
                {
                    "query": page["query"],
                    "page_number": page["page_number"],
                    "request_url": page["request_url"],
                    "response": page["raw_response"],
                }
            )

            for item in page["items"]:
                if item["source_id"] in seen_ids:
                    continue
                seen_ids.add(item["source_id"])
                items.append(item)
                if len(items) >= config.max_discussion_items:
                    break
            if len(items) >= config.max_discussion_items:
                break

        _save_debug(config, "latest_source1_raw.json", {"responses": debug_responses})
        diagnostics["live_items_fetched_count"] = len(items)

        logger.info("[Source 1] Live items fetched count: %s", len(items))
        if items:
            diagnostics["fallback_triggered"] = False
            logger.info("[Source 1] Fallback triggered? no")
            return items[: config.max_discussion_items], diagnostics

        return _with_fallback(config, diagnostics, "no_results", "Hacker News returned zero usable comment texts.")

    except COLLECTOR_FAILURES as exc:
        failure_type = _classify_failure(exc)
        _save_debug(
            config,
            "latest_source1_raw.json",
            {
                "request_urls": diagnostics.get("request_urls", []),
                "failure_type": failure_type,
                "failure_reason": str(exc),
            },
        )
        return _with_fallback(config, diagnostics, failure_type, str(exc))


def iter_discussion_pages(config, start_pages: dict[str, int] | None = None):
    queries = _queries_to_collect(config.community_queries, start_pages)
    if not queries:
        return
    page_plan = _page_plan(
        config.max_discussion_items,
        len(queries),
        config.discussion_page_size,
        config.discussion_max_pages_per_query,
    )
    for query in queries:
        start_page = _start_page(query, start_pages, 0)
        stop_page = start_page + page_plan["max_pages"]
        for page_number in range(start_page, stop_page):
            endpoint = _search_endpoint(config)
            query_params = {
                "query": query,
                "tags": "comment",
                "hitsPerPage": page_plan["page_size"],
                "page": page_number,
            }
            url = f"{endpoint}?{urlencode(query_params)}"
            logger.info("[Source 1] Query params: %s", query_params)
            logger.info("[Source 1] Request URL: %s", url)

            payload = _fetch_json_with_retries(url, config.request_timeout)
            hits = payload.get("hits")
            if not isinstance(hits, list):
                raise ValueError("Response JSON did not contain a list at key 'hits'.")

            items = [
                _map_hn_hit(hit, config.product_theme, query)
                for hit in hits
            ]
            items = [item for item in items if item["text"].strip()]
            nb_pages = payload.get("nbPages", page_number + 1)
            has_more = page_number + 1 < nb_pages and bool(hits)
            yield CollectedPage(
                source="source1_discussion",
                query=query,
                page_number=page_number,
                request_url=url,
                items=items,
                raw_count=len(hits),
                has_more=has_more,
                raw_response=payload,
            ).to_dict()
            if not has_more:
                break


def _page_plan(max_items: int, query_count: int, page_size_override: int = 0, max_pages_override: int = 0) -> dict:
    target_per_query = max(1, ceil(max_items / query_count))
    page_size = page_size_override or target_per_query
    page_size = max(1, min(page_size, 100))
    max_pages = max_pages_override or ceil(target_per_query / page_size)
    return {
        "page_size": page_size,
        "max_pages": max(1, max_pages),
    }


def _queries_to_collect(queries: list[str], start_pages: dict[str, int] | None) -> list[str]:
    if start_pages is None:
        return queries
    return [query for query in queries if query in start_pages]


def _start_page(query: str, start_pages: dict[str, int] | None, default: int) -> int:
    if start_pages is None:
        return default
    return start_pages[query]


def _base_diagnostics(config, queries: list[str]) -> dict:
    return CollectorDiagnostics(
        source="source1_discussion",
        endpoint=_search_endpoint(config),
        query_used=queries,
        expected_response_format="JSON object with 'hits' list; each hit may include comment_text, story_title, author, objectID.",
        debug_raw_file=str(config.raw_dir / "latest_source1_raw.json"),
    ).to_dict()


def _search_endpoint(config) -> str:
    if config.discussion_sort == "date":
        return HN_SEARCH_BY_DATE_ENDPOINT
    return HN_SEARCH_ENDPOINT


def _page_diagnostic(page: dict) -> dict:
    return {
        "source": page["source"],
        "query": page["query"],
        "page_number": page["page_number"],
        "request_url": page["request_url"],
        "request_params": page["request_params"],
        "raw_count": page["raw_count"],
        "item_count": len(page["items"]),
        "has_more": page["has_more"],
    }


def _fetch_json(url: str, timeout: int) -> dict:
    request = Request(url, headers={"User-Agent": "venture-signal-demo/1.0"})
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _fetch_json_with_retries(url: str, timeout: int) -> dict:
    last_error = None
    for attempt in range(3):
        try:
            return _fetch_json(url, timeout)
        except COLLECTOR_FAILURES as exc:
            last_error = exc
            if attempt < 2:
                sleep_seconds = 1 + attempt
                logger.info("[Source 1] Request failed on attempt %s; retrying in %ss. Reason: %s", attempt + 1, sleep_seconds, exc)
                time.sleep(sleep_seconds)
    raise last_error


def _map_hn_hit(hit: dict, product_theme: str, query: str) -> dict:
    object_id = hit.get("objectID", "")
    story_id = hit.get("story_id") or hit.get("parent_id") or object_id
    return RawItem(
        source_type="discussion",
        source_name="Hacker News Algolia comments",
        source_id=object_id,
        source_url=f"https://news.ycombinator.com/item?id={story_id}",
        title=hit.get("story_title") or "Hacker News discussion",
        author=hit.get("author") or "unknown",
        created_at=hit.get("created_at") or "",
        collected_at=datetime.now(timezone.utc).isoformat(),
        product_theme=product_theme,
        query_theme=query,
        text=hit.get("comment_text") or "",
    ).to_dict()


def _with_fallback(config, diagnostics: dict, failure_type: str, reason: str) -> tuple[list[dict], dict]:
    fallback_items = _fallback_discussion_items(config, reason)
    diagnostics["fallback_triggered"] = True
    diagnostics["fallback_reason"] = reason
    diagnostics["failure_type"] = failure_type
    diagnostics["fallback_items_inserted"] = len(fallback_items)
    logger.info("[Source 1] Live items fetched count: %s", diagnostics["live_items_fetched_count"])
    logger.info("[Source 1] Fallback triggered? yes")
    logger.info("[Source 1] Failure type: %s", failure_type)
    logger.info("[Source 1] Failure reason: %s", reason)
    logger.info("[Source 1] Starting fallback: inserting %s built-in discussion records.", len(fallback_items))
    return fallback_items, diagnostics


def _fallback_discussion_items(config, reason: str) -> list[dict]:
    now = datetime.now(timezone.utc).isoformat()
    examples = [
        ("small business workflow pain", "Small business owners keep saying operations work is scattered across invoices, scheduling, CRM updates, and follow-ups. The hard part is keeping the workflow moving without a full operations team."),
        ("admin automation frustration", "I tried automating admin tasks for my one-person business, but setup took longer than doing the work manually. The tools assume I have time to maintain another system."),
        ("CRM frustration small business", "Teams compare CRM, scheduling, and invoicing tools, but complain that business software is too complicated for a lean team that just needs lightweight follow-through."),
        ("solo founder automation", "The demand is real for automation that helps solo operators, but trust, integrations, and accuracy concerns slow adoption when the tool touches customer or payment workflows."),
    ]
    return [
        RawItem(
            source_type="discussion",
            source_name="Hacker News Algolia comments",
            source_id=f"fallback-hn-{index}",
            source_url="https://hn.algolia.com/",
            title="Built-in discussion fallback record",
            author="demo-fallback",
            created_at=now,
            collected_at=now,
            product_theme=config.product_theme,
            query_theme=query,
            text=text,
            is_demo_fallback=True,
            fallback_label="FALLBACK_DERIVED_EVIDENCE",
            fallback_reason=reason,
        ).to_dict()
        for index, (query, text) in enumerate(examples, start=1)
    ]


def _save_debug(config, filename: str, data: dict) -> None:
    if not config.debug_save_raw:
        return
    path = config.raw_dir / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("[Source 1] Debug raw response saved: %s", path)


def _classify_failure(exc: Exception) -> str:
    if isinstance(exc, HTTPError):
        if exc.code == 429:
            return "rate_limiting"
        if 500 <= exc.code <= 599:
            return "endpoint_unavailable"
        if 400 <= exc.code <= 499:
            return "bad_query_or_client_error"
        return "http_error"
    if isinstance(exc, (JSONDecodeError, ValueError)):
        return "parsing_issue"
    if isinstance(exc, (URLError, TimeoutError, socket.timeout)):
        return "endpoint_unavailable"
    return "other_failure"
