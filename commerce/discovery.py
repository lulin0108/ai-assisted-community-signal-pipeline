"""Discover public product and feedback leads through a bounded search provider."""

from datetime import datetime, timezone
from html.parser import HTMLParser
import re
from unicodedata import normalize
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import requests


SEARCH_ENDPOINT = "https://api.search.brave.com/res/v1/web/search"
MARKETS = {"US", "CA", "GB"}
RESULT_LIMIT = 8
ZH_TERMS = {
    "宠物喂食": "pet feeding station", "宠物餐垫": "pet feeding mat",
    "狗狗喝水": "dog water bowl spills", "猫咪喝水": "cat water bowl spills",
    "集水": "drip tray", "防溅": "splash guard", "积水": "standing water",
    "防滑": "non-slip", "易清洗": "easy to clean", "清洁": "cleaning",
    "桌下理线": "under desk cable management", "理线": "cable management",
    "抽屉收纳": "drawer organization", "抽屉分隔": "drawer dividers",
    "浴室收纳": "bathroom storage", "厨房收纳": "kitchen storage",
    "旅行收纳": "travel organizers", "旅行分装": "travel toiletry containers",
    "汽车收纳": "car organizers", "车载收纳": "car organizers",
}
PUBLISHERS = {
    "amazon.com", "amazon.ca", "amazon.co.uk", "walmart.com", "walmart.ca",
    "chewy.com", "target.com", "etsy.com", "ebay.com", "ebay.ca", "ebay.co.uk",
}
PRODUCT_PATH = re.compile(r"/(?:products|product|dp|gp/product|ip|p|itm|listing)/[^/?]+", re.I)
REVIEW_PAGE = re.compile(r"product-reviews|customer-reviews|/reviews?/|/forum[s]?/|/thread[s]?/|/topic[s]?/", re.I)
BUYER_WORDS = re.compile(r"\b(?:customer|buyer|user|verified purchase|owner) reviews?\b|\b(?:i|we) (?:bought|used|tried|returned)\b|用户评价|买家评价|差评", re.I)
EDITORIAL = re.compile(r"\b(?:roundup|buying guide|top \d+|\d+ best)\b|购买指南|排行榜", re.I)
THEME_RULES = {
    "cleanup": re.compile(r"hard to clean|difficult to clean|difficult to wash|mold|mould|residue|难清洗|难清理|发霉", re.I),
    "fit": re.compile(r"too small|too big|too large|doesn.t fit|didn.t fit|won.t fit|尺寸不合|装不下|太小|太大", re.I),
    "leaks": re.compile(r"\bleaks?\b|\bleakage\b|spills out|doesn.t seal|漏水|渗水|漏液|溢出", re.I),
    "wear": re.compile(r"\bbroke\b|\bcracked\b|falls apart|fell apart|torn|断裂|开裂|不耐用", re.I),
    "setup": re.compile(r"hard to install|difficult to install|difficult to assemble|hard to assemble|安装困难|难安装", re.I),
}
NEGATED = re.compile(r"\b(?:no|not|never|without|zero|prevent(?:s|ed|ing)?|stops?)\b(?:\W+\w+){0,3}\W*$|(?:没有|从不|避免|防止|防)[^，。！？]{0,4}$", re.I)


class DiscoveryError(Exception):
    """A provider failure safe to communicate to the browser."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


class PlainText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def clean_text(value, limit):
    parser = PlainText()
    parser.feed(value if isinstance(value, str) else "")
    parser.close()
    return " ".join("".join(parser.parts).split())[:limit]


def build_queries(scene, keywords=""):
    brief = " ".join(normalize("NFKC", scene).split())
    translated = list(dict.fromkeys(value for key, value in ZH_TERMS.items() if key in brief))
    core = " ".join(translated) if translated else ""
    terms = " ".join(normalize("NFKC", keywords).split()) or core or brief
    # Preserve the original scene in the search plan when a short term list is used.
    core = " ".join(terms.split()[:52])[:370]
    original = " ".join(brief.split()[:52])[:370]
    query_templates = [
        ("products", f"{core} product buy"),
        ("feedback", f"{core} customer reviews complaints problems"),
        ("alternatives", f"{core} alternatives comparison"),
    ]
    if core != original:
        query_templates.append(("original", original))
    return [{"kind": kind, "query": query} for kind, query in query_templates]


def canonical_url(raw_url):
    if not isinstance(raw_url, str):
        return None
    try:
        parts = urlsplit(raw_url)
        host = (parts.hostname or "").lower().removeprefix("www.")
        if parts.scheme != "https" or not host or "." not in host or parts.username or parts.password or parts.port:
            return None
    except ValueError:
        return None
    if any(host == root or host.endswith("." + root) for root in ("reddit.com", "redd.it")):
        return None
    path = parts.path.rstrip("/") or "/"
    if host in {"amazon.com", "amazon.ca", "amazon.co.uk"}:
        asin = re.search(r"/(dp|gp/product|product-reviews)/([A-Z0-9]{10})(?:/|$)", path, re.I)
        if asin:
            section = "product-reviews" if asin[1].lower() == "product-reviews" else "dp"
            return urlunsplit(("https", host, f"/{section}/{asin[2].upper()}", "", "")), host, f"/{section}/{asin[2].upper()}"
    # Preserve identifiers on query-based product pages while removing trackers.
    query = urlencode(sorted((key, value) for key, value in parse_qsl(parts.query) if not (
        key.lower().startswith("utm_") or key.lower() in {"ref", "tag", "gclid", "fbclid"}
    )))
    return urlunsplit(("https", parts.hostname, path, query, "")), host, path


def normalize_result(row):
    parsed = canonical_url(row.get("url"))
    title = clean_text(row.get("title"), 180)
    if not parsed or not title:
        return None
    url, host, path = parsed
    summary = clean_text(row.get("description"), 360)
    product = row.get("product")
    if REVIEW_PAGE.search(path):
        kind = "feedback"
    elif EDITORIAL.search(title):
        kind = "reference"
    elif PRODUCT_PATH.search(path) or (host in PUBLISHERS and isinstance(product, dict) and product):
        kind = "product"
    elif BUYER_WORDS.search(f"{title} {summary}"):
        kind = "feedback"
    else:
        kind = "reference"
    return {"url": url, "source": host, "title": title, "summary": summary, "kind": kind}


def fetch_results(query, market, token):
    try:
        response = requests.get(
            SEARCH_ENDPOINT,
            params={"q": query, "country": market, "count": RESULT_LIMIT, "safesearch": "moderate"},
            headers={"X-Subscription-Token": token, "Accept": "application/json"},
            timeout=(3.5, 8),
            allow_redirects=False,
        )
        if response.status_code in {401, 403}:
            raise DiscoveryError("auth")
        if response.status_code == 429:
            raise DiscoveryError("quota")
        if response.status_code != 200:
            raise DiscoveryError("provider")
        rows = response.json().get("web", {}).get("results", [])
        if not isinstance(rows, list):
            raise DiscoveryError("provider")
        return [row for row in rows[:RESULT_LIMIT] if isinstance(row, dict)]
    except requests.Timeout as exc:
        raise DiscoveryError("timeout") from exc
    except (requests.RequestException, ValueError, AttributeError) as exc:
        raise DiscoveryError("provider") from exc


def build_themes(feedback):
    themes = []
    for key, pattern in THEME_RULES.items():
        hits = []
        for entry in feedback:
            text = entry["summary"]
            if any(not NEGATED.search(text[max(0, match.start() - 40):match.start()]) for match in pattern.finditer(text)):
                hits.append(entry["url"])
        if hits:
            themes.append({"id": key, "urls": hits})
    return sorted(themes, key=lambda item: -len(item["urls"]))


def discover(scene, market, token, keywords=""):
    searches = build_queries(scene, keywords)
    leads = {}
    completed = 0
    last_error = None
    for search in searches:
        try:
            rows = fetch_results(search["query"], market, token)
        except DiscoveryError as exc:
            search["error"] = exc.code
            last_error = exc
            # Avoid additional requests after a quota or authorization failure.
            if exc.code in {"auth", "quota"}:
                break
            continue
        completed += 1
        search["results"] = len(rows)
        for row in rows:
            entry = normalize_result(row)
            if entry:
                key = entry["url"].replace("https://www.", "https://", 1)
                leads.setdefault(key, entry)
    if completed == 0 or (not leads and last_error):
        raise last_error or DiscoveryError("provider")
    groups = {kind: [entry for entry in leads.values() if entry["kind"] == kind] for kind in ("product", "feedback", "reference")}
    return {
        "market": market, "searched_at": datetime.now(timezone.utc).isoformat(),
        "state": ("partial" if any("error" in search for search in searches) else "ok") if leads else "empty",
        "groups": groups, "themes": build_themes(groups["feedback"]),
        "searches": [search for search in searches if "results" in search or "error" in search],
    }
