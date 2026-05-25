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
import socket


HN_SEARCH_ENDPOINT = "https://hn.algolia.com/api/v1/search"


def collect_discussion_items(config) -> tuple[list[dict], dict]:
    queries = config.community_queries
    hits_per_query = max(1, ceil(config.max_discussion_items / len(queries)))
    diagnostics = _base_diagnostics(config, queries)

    print("[Source 1] Public discussion/community source")
    print(f"[Source 1] Endpoint: {HN_SEARCH_ENDPOINT}")
    print(f"[Source 1] Query family: {queries}")
    print("[Source 1] Expected response: JSON object with a 'hits' list of Hacker News comment records.")

    try:
        items = []
        seen_ids = set()
        debug_responses = []

        for query in queries:
            query_params = {
                "query": query,
                "tags": "comment",
                "hitsPerPage": hits_per_query,
            }
            url = f"{HN_SEARCH_ENDPOINT}?{urlencode(query_params)}"
            diagnostics["request_urls"].append(url)
            print(f"[Source 1] Query params: {query_params}")
            print(f"[Source 1] Request URL: {url}")

            payload = _fetch_json(url, config.request_timeout)
            debug_responses.append({"query": query, "request_url": url, "response": payload})

            hits = payload.get("hits")
            if not isinstance(hits, list):
                return _with_fallback(config, diagnostics, "parsing_issue", "Response JSON did not contain a list at key 'hits'.")

            for hit in hits:
                item = _map_hn_hit(hit, config.product_theme, query)
                if not item["text"].strip():
                    continue
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

        print(f"[Source 1] Live items fetched count: {len(items)}")
        if items:
            diagnostics["fallback_triggered"] = False
            print("[Source 1] Fallback triggered? no")
            return items[: config.max_discussion_items], diagnostics

        return _with_fallback(config, diagnostics, "no_results", "Hacker News returned zero usable comment texts.")

    except Exception as exc:
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


def _base_diagnostics(config, queries: list[str]) -> dict:
    return {
        "source": "source1_discussion",
        "endpoint": HN_SEARCH_ENDPOINT,
        "query_used": queries,
        "request_urls": [],
        "expected_response_format": "JSON object with 'hits' list; each hit may include comment_text, story_title, author, objectID.",
        "live_items_fetched_count": 0,
        "fallback_triggered": None,
        "fallback_reason": "",
        "failure_type": "",
        "fallback_items_inserted": 0,
        "debug_raw_file": str(config.raw_dir / "latest_source1_raw.json"),
    }


def _fetch_json(url: str, timeout: int) -> dict:
    request = Request(url, headers={"User-Agent": "venture-signal-demo/1.0"})
    with urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _map_hn_hit(hit: dict, product_theme: str, query: str) -> dict:
    object_id = hit.get("objectID", "")
    story_id = hit.get("story_id") or hit.get("parent_id") or object_id
    return {
        "source_type": "discussion",
        "source_name": "Hacker News Algolia comments",
        "source_id": object_id,
        "source_url": f"https://news.ycombinator.com/item?id={story_id}",
        "title": hit.get("story_title") or "Hacker News discussion",
        "author": hit.get("author") or "unknown",
        "created_at": hit.get("created_at") or "",
        "collected_at": datetime.now(timezone.utc).isoformat(),
        "product_theme": product_theme,
        "query_theme": query,
        "text": hit.get("comment_text") or "",
        "is_demo_fallback": False,
    }


def _with_fallback(config, diagnostics: dict, failure_type: str, reason: str) -> tuple[list[dict], dict]:
    fallback_items = _fallback_discussion_items(config, reason)
    diagnostics["fallback_triggered"] = True
    diagnostics["fallback_reason"] = reason
    diagnostics["failure_type"] = failure_type
    diagnostics["fallback_items_inserted"] = len(fallback_items)
    print(f"[Source 1] Live items fetched count: {diagnostics['live_items_fetched_count']}")
    print("[Source 1] Fallback triggered? yes")
    print(f"[Source 1] Failure type: {failure_type}")
    print(f"[Source 1] Failure reason: {reason}")
    print(f"[Source 1] Starting fallback: inserting {len(fallback_items)} built-in discussion records.")
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
        {
            "source_type": "discussion",
            "source_name": "Hacker News Algolia comments",
            "source_id": f"fallback-hn-{index}",
            "source_url": "https://hn.algolia.com/",
            "title": "Built-in discussion fallback record",
            "author": "demo-fallback",
            "created_at": now,
            "collected_at": now,
            "product_theme": config.product_theme,
            "query_theme": query,
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
    print(f"[Source 1] Debug raw response saved: {path}")


def _classify_failure(exc: Exception) -> str:
    if isinstance(exc, HTTPError):
        if exc.code == 429:
            return "rate_limiting"
        if 500 <= exc.code <= 599:
            return "endpoint_unavailable"
        if 400 <= exc.code <= 499:
            return "bad_query_or_client_error"
        return "http_error"
    if isinstance(exc, JSONDecodeError):
        return "parsing_issue"
    if isinstance(exc, (URLError, TimeoutError, socket.timeout)):
        return "endpoint_unavailable"
    return "other_failure"
