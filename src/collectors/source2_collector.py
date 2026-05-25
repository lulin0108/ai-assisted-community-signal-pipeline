"""Collector for Source Type 2: public Stack Overflow questions.

Stack Overflow questions are used as feedback-style evidence for practical
implementation barriers: setup friction, integration problems, API confusion,
workflow automation errors, and dissatisfaction with current tools.
"""

from datetime import datetime, timezone
from html import unescape
from json import JSONDecodeError
import json
from math import ceil
import re
import time

import requests


STACKEXCHANGE_SEARCH_ENDPOINT = "https://api.stackexchange.com/2.3/search/advanced"


def collect_review_items(config) -> tuple[list[dict], dict]:
    diagnostics = _base_diagnostics(config)
    session = requests.Session()
    session.headers.update({"User-Agent": "ai-venture-signal-pipeline/1.0"})

    print("[Source 2] Public implementation-feedback source")
    print(f"[Source 2] Stack Exchange endpoint: {STACKEXCHANGE_SEARCH_ENDPOINT}")
    print(f"[Source 2] Stack Exchange site: {config.stackexchange_site}")
    print(f"[Source 2] Stack Exchange query family: {config.stackexchange_queries}")
    print("[Source 2] Expected response: JSON object with an 'items' list of public Stack Overflow questions.")

    debug_payload = {"query_responses": []}

    try:
        items = []
        seen_ids = set()
        pagesize = max(1, min(ceil(config.max_review_items / len(config.stackexchange_queries)), 100))

        for query in config.stackexchange_queries:
            params = {
                "order": "desc",
                "sort": "activity",
                "site": config.stackexchange_site,
                "q": query,
                "pagesize": pagesize,
                "filter": "withbody",
            }
            diagnostics["request_params"].append(params)
            print(f"[Source 2] Query: {query}")
            print(f"[Source 2] Request params: {params}")

            payload = _get_json_with_retries(session, STACKEXCHANGE_SEARCH_ENDPOINT, params, config.request_timeout)
            debug_payload["query_responses"].append({"query": query, "params": params, "response": payload})

            questions = payload.get("items")
            if not isinstance(questions, list):
                _save_debug(config, "latest_source2_raw.json", debug_payload)
                return _with_fallback(config, diagnostics, "parsing_issue", "Stack Exchange response did not contain a list at key 'items'.")

            diagnostics["live_question_count_fetched"] += len(questions)
            for question in questions:
                question_id = question.get("question_id")
                if question_id in seen_ids:
                    continue
                seen_ids.add(question_id)
                mapped = _map_stackoverflow_question(question, query, config)
                if mapped["text"].strip():
                    items.append(mapped)
                if len(items) >= config.max_review_items:
                    break
            if len(items) >= config.max_review_items:
                break

        _save_debug(config, "latest_source2_raw.json", debug_payload)
        diagnostics["live_items_fetched_count"] = len(items)
        print(f"[Source 2] Live question count fetched: {diagnostics['live_question_count_fetched']}")
        print(f"[Source 2] Live usable question items fetched: {len(items)}")

        if items:
            diagnostics["fallback_triggered"] = False
            print("[Source 2] Fallback triggered? no")
            return items, diagnostics

        return _with_fallback(config, diagnostics, "no_results", "Stack Exchange returned zero usable public questions for the query family.")

    except Exception as exc:
        failure_type = _classify_failure(exc)
        debug_payload["failure_type"] = failure_type
        debug_payload["failure_reason"] = str(exc)
        _save_debug(config, "latest_source2_raw.json", debug_payload)
        return _with_fallback(config, diagnostics, failure_type, str(exc))


def _base_diagnostics(config) -> dict:
    return {
        "source": "source2_stackoverflow_questions",
        "endpoint": STACKEXCHANGE_SEARCH_ENDPOINT,
        "stackexchange_site": config.stackexchange_site,
        "stackexchange_query": config.stackexchange_queries,
        "request_params": [],
        "expected_response_format": "JSON object with 'items'; each item may include question_id, title, body, link, owner, tags, score, and answer_count.",
        "live_question_count_fetched": 0,
        "live_items_fetched_count": 0,
        "fallback_triggered": None,
        "fallback_reason": "",
        "failure_type": "",
        "fallback_items_inserted": 0,
        "debug_raw_file": str(config.raw_dir / "latest_source2_raw.json"),
    }


def _get_json_with_retries(session: requests.Session, url: str, params: dict, timeout: int) -> dict:
    last_error = None
    for attempt in range(3):
        try:
            response = session.get(url, params=params, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, JSONDecodeError, ValueError) as exc:
            last_error = exc
            if attempt < 2:
                sleep_seconds = 1 + attempt
                print(f"[Source 2] Request failed on attempt {attempt + 1}; retrying in {sleep_seconds}s. Reason: {exc}")
                time.sleep(sleep_seconds)
    raise last_error


def _map_stackoverflow_question(question: dict, query: str, config) -> dict:
    owner = question.get("owner") or {}
    body_text = _clean_html(question.get("body", ""))
    tags = ", ".join(question.get("tags", []))
    title = unescape(question.get("title", "Stack Overflow question"))
    text = f"{title}. {body_text}"
    return {
        "source_type": "review",
        "source_name": "Stack Overflow public questions",
        "source_id": str(question.get("question_id", "unknown-question")),
        "source_url": question.get("link") or "https://stackoverflow.com/",
        "title": title,
        "author": owner.get("display_name", "unknown"),
        "created_at": _unix_to_iso(question.get("creation_date")),
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "product_theme": config.product_theme,
        "query_theme": query,
        "reviewed_product": tags,
        "rating": str(question.get("score", "")),
        "text": text,
        "is_demo_fallback": False,
    }


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
    print(f"[Source 2] Live question count fetched: {diagnostics['live_question_count_fetched']}")
    print(f"[Source 2] Live usable question items fetched: {diagnostics['live_items_fetched_count']}")
    print("[Source 2] Fallback triggered? yes")
    print(f"[Source 2] Failure type: {failure_type}")
    print(f"[Source 2] Failure reason: {reason}")
    print(f"[Source 2] Starting fallback: inserting {len(fallback_items)} built-in Stack Overflow-style feedback records.")
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
        {
            "source_type": "review",
            "source_name": "Stack Overflow public questions",
            "source_id": f"fallback-stackoverflow-question-{index}",
            "source_url": "https://stackoverflow.com/",
            "title": query,
            "author": "demo-fallback",
            "created_at": now,
            "collected_at": now,
            "product_theme": config.product_theme,
            "query_theme": query,
            "reviewed_product": "",
            "rating": "",
            "text": text,
            "is_demo_fallback": True,
            "fallback_label": "FALLBACK_DERIVED_EVIDENCE",
            "fallback_reason": reason,
        }
        for index, (query, text) in enumerate(examples, start=1)
    ]


def _save_debug(config, filename: str, data: dict) -> None:
    if not config.debug_save_raw:
        return
    path = config.raw_dir / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[Source 2] Debug raw response saved: {path}")


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
