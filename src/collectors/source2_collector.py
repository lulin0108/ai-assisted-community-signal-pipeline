"""Collector for Source Type 2: public Stack Overflow questions.

Stack Overflow questions are used as feedback-style evidence for practical
implementation barriers: setup friction, integration problems, API confusion,
workflow automation errors, and dissatisfaction with current tools.
"""

from datetime import datetime, timezone
from html import unescape
from json import JSONDecodeError
import json
import logging
from math import ceil
import re
import time

import requests

from models import CollectedPage, CollectorDiagnostics, RawItem


STACKEXCHANGE_SEARCH_ENDPOINT = "https://api.stackexchange.com/2.3/search/advanced"
COLLECTOR_FAILURES = (requests.RequestException, JSONDecodeError, ValueError)
logger = logging.getLogger(__name__)


def collect_review_items(config, start_pages: dict[str, int] | None = None) -> tuple[list[dict], dict]:
    diagnostics = _base_diagnostics(config)
    diagnostics["resume_start_pages"] = start_pages or {}

    logger.info("[Source 2] Public implementation-feedback source")
    logger.info("[Source 2] Stack Exchange endpoint: %s", STACKEXCHANGE_SEARCH_ENDPOINT)
    logger.info("[Source 2] Stack Exchange site: %s", config.stackexchange_site)
    logger.info("[Source 2] Stack Exchange query family: %s", config.stackexchange_queries)
    if start_pages is not None:
        logger.info("[Source 2] Resume start pages: %s", start_pages)
    logger.info("[Source 2] Expected response: JSON object with an 'items' list of public Stack Overflow questions.")

    debug_payload = {"query_responses": []}

    try:
        items = []
        seen_ids = set()

        if not _queries_to_collect(config.stackexchange_queries, start_pages):
            diagnostics["fallback_triggered"] = False
            return [], diagnostics

        for page in iter_review_pages(config, start_pages):
            diagnostics["request_params"].append(page["request_params"])
            diagnostics["collected_pages"].append(_page_diagnostic(page))
            debug_payload["query_responses"].append(
                {
                    "query": page["query"],
                    "page_number": page["page_number"],
                    "params": page["request_params"],
                    "response": page["raw_response"],
                }
            )

            diagnostics["live_question_count_fetched"] += page["raw_count"]
            for item in page["items"]:
                if item["source_id"] in seen_ids:
                    continue
                seen_ids.add(item["source_id"])
                items.append(item)
                if len(items) >= config.max_review_items:
                    break
            if len(items) >= config.max_review_items:
                break

        _save_debug(config, "latest_source2_raw.json", debug_payload)
        diagnostics["live_items_fetched_count"] = len(items)
        logger.info("[Source 2] Live question count fetched: %s", diagnostics["live_question_count_fetched"])
        logger.info("[Source 2] Live usable question items fetched: %s", len(items))

        if items:
            diagnostics["fallback_triggered"] = False
            logger.info("[Source 2] Fallback triggered? no")
            return items, diagnostics

        return _with_fallback(config, diagnostics, "no_results", "Stack Exchange returned zero usable public questions for the query family.")

    except COLLECTOR_FAILURES as exc:
        failure_type = _classify_failure(exc)
        debug_payload["failure_type"] = failure_type
        debug_payload["failure_reason"] = str(exc)
        _save_debug(config, "latest_source2_raw.json", debug_payload)
        return _with_fallback(config, diagnostics, failure_type, str(exc))


def iter_review_pages(config, start_pages: dict[str, int] | None = None):
    queries = _queries_to_collect(config.stackexchange_queries, start_pages)
    if not queries:
        return
    page_plan = _page_plan(
        config.max_review_items,
        len(queries),
        config.review_page_size,
        config.review_max_pages_per_query,
    )
    session = requests.Session()
    session.headers.update({"User-Agent": "ai-venture-signal-pipeline/1.0"})
    try:
        for query in queries:
            start_page = _start_page(query, start_pages, 1)
            stop_page = start_page + page_plan["max_pages"]
            for page_number in range(start_page, stop_page):
                params = {
                    "order": config.review_order,
                    "sort": config.review_sort,
                    "site": config.stackexchange_site,
                    "q": query,
                    "pagesize": page_plan["page_size"],
                    "page": page_number,
                    "filter": "withbody",
                }
                logger.info("[Source 2] Query: %s", query)
                logger.info("[Source 2] Request params: %s", params)

                payload = _get_json_with_retries(session, STACKEXCHANGE_SEARCH_ENDPOINT, params, config.request_timeout)
                questions = payload.get("items")
                if not isinstance(questions, list):
                    raise ValueError("Stack Exchange response did not contain a list at key 'items'.")

                items = [
                    _map_stackoverflow_question(question, query, config)
                    for question in questions
                ]
                items = [item for item in items if item["text"].strip()]
                has_more = bool(payload.get("has_more")) and bool(questions)
                yield CollectedPage(
                    source="source2_stackoverflow_questions",
                    query=query,
                    page_number=page_number,
                    request_params=params,
                    items=items,
                    raw_count=len(questions),
                    has_more=has_more,
                    raw_response=payload,
                ).to_dict()
                if not has_more:
                    break
    finally:
        session.close()


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


def _base_diagnostics(config) -> dict:
    return CollectorDiagnostics(
        source="source2_stackoverflow_questions",
        endpoint=STACKEXCHANGE_SEARCH_ENDPOINT,
        stackexchange_site=config.stackexchange_site,
        stackexchange_query=config.stackexchange_queries,
        expected_response_format="JSON object with 'items'; each item may include question_id, title, body, link, owner, tags, score, and answer_count.",
        debug_raw_file=str(config.raw_dir / "latest_source2_raw.json"),
    ).to_dict()


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


def _get_json_with_retries(session: requests.Session, url: str, params: dict, timeout: int) -> dict:
    last_error = None
    for attempt in range(3):
        try:
            response = session.get(url, params=params, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except COLLECTOR_FAILURES as exc:
            last_error = exc
            if attempt < 2:
                sleep_seconds = 1 + attempt
                logger.info("[Source 2] Request failed on attempt %s; retrying in %ss. Reason: %s", attempt + 1, sleep_seconds, exc)
                time.sleep(sleep_seconds)
    raise last_error


def _map_stackoverflow_question(question: dict, query: str, config) -> dict:
    owner = question.get("owner") or {}
    body_text = _clean_html(question.get("body", ""))
    tags = ", ".join(question.get("tags", []))
    title = unescape(question.get("title", "Stack Overflow question"))
    text = f"{title}. {body_text}"
    return RawItem(
        source_type="review",
        source_name="Stack Overflow public questions",
        source_id=str(question.get("question_id", "unknown-question")),
        source_url=question.get("link") or "https://stackoverflow.com/",
        title=title,
        author=owner.get("display_name", "unknown"),
        created_at=_unix_to_iso(question.get("creation_date")),
        collected_at=datetime.now(timezone.utc).isoformat(),
        product_theme=config.product_theme,
        query_theme=query,
        reviewed_product=tags,
        rating=str(question.get("score", "")),
        text=text,
    ).to_dict()


def _clean_html(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", value or "")
    text = unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _unix_to_iso(value: int | None) -> str:
    if not value:
        return ""
    return datetime.fromtimestamp(value, timezone.utc).isoformat()


def _with_fallback(config, diagnostics: dict, failure_type: str, reason: str) -> tuple[list[dict], dict]:
    fallback_items = _fallback_review_items(config, reason)
    diagnostics["fallback_triggered"] = True
    diagnostics["fallback_reason"] = reason
    diagnostics["failure_type"] = failure_type
    diagnostics["fallback_items_inserted"] = len(fallback_items)
    logger.info("[Source 2] Live question count fetched: %s", diagnostics["live_question_count_fetched"])
    logger.info("[Source 2] Live usable question items fetched: %s", diagnostics["live_items_fetched_count"])
    logger.info("[Source 2] Fallback triggered? yes")
    logger.info("[Source 2] Failure type: %s", failure_type)
    logger.info("[Source 2] Failure reason: %s", reason)
    logger.info("[Source 2] Starting fallback: inserting %s built-in Stack Overflow-style feedback records.", len(fallback_items))
    return fallback_items, diagnostics


def _fallback_review_items(config, reason: str) -> list[dict]:
    now = datetime.now(timezone.utc).isoformat()
    examples = [
        ("workflow automation integration", "I am trying to connect a workflow automation tool to our invoicing system, but the API errors are unclear and the setup takes too long for a small team."),
        ("crm api integration problem", "Our CRM integration works for simple cases, but syncing customer records fails when fields are missing. I still have to fix records manually."),
        ("zapier automation error", "The automation looks useful, but troubleshooting each failed step is hard for a one-person business without a developer on staff."),
        ("n8n setup issue", "I want to self-host an automation workflow, but onboarding and credential setup are confusing before I can get value from the tool."),
    ]
    return [
        RawItem(
            source_type="review",
            source_name="Stack Overflow public questions",
            source_id=f"fallback-stackoverflow-question-{index}",
            source_url="https://stackoverflow.com/",
            title=query,
            author="demo-fallback",
            created_at=now,
            collected_at=now,
            product_theme=config.product_theme,
            query_theme=query,
            reviewed_product="",
            rating="",
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
    logger.info("[Source 2] Debug raw response saved: %s", path)


def _classify_failure(exc: Exception) -> str:
    if isinstance(exc, requests.HTTPError):
        status_code = exc.response.status_code if exc.response is not None else None
        if status_code in {403, 429}:
            return "rate_limiting_or_forbidden"
        if status_code and 500 <= status_code <= 599:
            return "endpoint_unavailable"
        if status_code and 400 <= status_code <= 499:
            return "bad_query_or_client_error"
        return "http_error"
    if isinstance(exc, (requests.Timeout, requests.ConnectionError)):
        return "endpoint_unavailable"
    if isinstance(exc, requests.RequestException):
        return "endpoint_unavailable"
    if isinstance(exc, (JSONDecodeError, ValueError)):
        return "parsing_issue"
    return "other_failure"
