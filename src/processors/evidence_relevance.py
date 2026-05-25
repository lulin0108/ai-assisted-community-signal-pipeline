"""Score evidence relevance for the current venture-category scope."""

from collections import Counter
import re


BUSINESS_SCOPE_TERMS = [
    "small business",
    "one-person",
    "solo",
    "solo founder",
    "lean team",
    "small team",
    "small company",
    "owner",
    "customer",
    "customers",
    "admin",
    "operations",
    "invoicing",
    "invoice",
    "crm",
    "scheduling",
    "customer records",
    "follow-up",
    "bookkeeping",
    "payroll",
    "sales pipeline",
    "lead",
    "leads",
]

WORKFLOW_FRICTION_TERMS = [
    "workflow",
    "workflow automation",
    "manual work",
    "manual process",
    "manual cleanup",
    "too many tools",
    "scattered",
    "handoff",
    "follow-up",
    "repeatable",
    "repetitive",
    "busywork",
    "automation",
    "automate",
    "operational",
    "operations",
]

PRACTICAL_TOOL_TERMS = [
    "zapier",
    "n8n",
    "airtable",
    "hubspot",
    "salesforce",
    "quickbooks",
    "stripe",
    "shopify",
    "notion",
    "slack",
    "google sheets",
    "crm",
    "invoicing",
    "scheduling",
]

AI_OPERATIONAL_TERMS = [
    "ai",
    "llm",
    "agent",
    "assistant",
    "copilot",
    "ai-enabled",
]

TECHNICAL_DETAIL_TERMS = [
    "api",
    "apis",
    "endpoint",
    "json",
    "python",
    "javascript",
    "typescript",
    "docker",
    "kubernetes",
    "database",
    "sql",
    "server",
    "oauth",
    "token",
    "stack trace",
    "library",
    "package",
    "dependency",
    "sdk",
    "webhook",
    "http",
    "request",
    "response",
    "runtime",
    "deployment",
    "container",
    "hosting",
]

TECHNICAL_CONTEXT_ALLOW_TERMS = BUSINESS_SCOPE_TERMS + WORKFLOW_FRICTION_TERMS + PRACTICAL_TOOL_TERMS + [
    "integration",
    "sync",
]

CONTEXT_ANCHOR_TERMS = BUSINESS_SCOPE_TERMS + WORKFLOW_FRICTION_TERMS + PRACTICAL_TOOL_TERMS + [
    "business",
    "client",
    "clients",
    "company",
    "founder",
    "operator",
    "accounting",
    "support",
    "sales",
    "marketing",
    "integration",
    "api",
    "webhook",
    "setup",
    "onboarding",
    "permission",
    "tool",
    "tools",
    "saas",
]

ADOPTION_RELEVANCE_TERMS = [
    "setup",
    "install",
    "configure",
    "configuration",
    "onboarding",
    "permission",
    "credential",
    "authentication",
    "integration",
    "api",
    "sync",
    "migration",
    "switching",
    "too complex",
    "hard to use",
    "learning curve",
    "workflow",
    "workflow burden",
    "switching cost",
]

DISSATISFACTION_RELEVANCE_TERMS = [
    "frustrating",
    "too complicated",
    "complicated",
    "doesn't work",
    "not working",
    "fails",
    "failed",
    "error",
    "missing",
    "manual",
    "still have to",
    "wrong",
    "inaccurate",
    "poor fit",
    "doesn't fit",
    "not useful",
    "slow",
    "broken",
    "support",
]

PROMOTION_PATTERNS = [
    "show hn",
    "launch hn",
    "hi hn",
    "i'm one of the creators",
    "i am one of the creators",
    "i'm the founder",
    "i am the founder",
    "as the founder",
    "i built",
    "i made",
    "i launched",
    "i just launched",
    "we just launched",
    "check out",
    "try my",
    "my startup",
    "my product",
    "my app",
    "we built",
    "we launched",
    "we're launching",
    "we are launching",
    "our product",
    "our app",
    "our platform",
    "product hunt",
    "sign up",
    "book a demo",
    "landing page",
    "waitlist",
    "request for feedback",
    "would love feedback",
    "introducing",
]

GENERIC_ENTERPRISE_TERMS = [
    "sharepoint",
    "enterprise",
    "corporate",
    "fortune 500",
    "large organization",
]

QUOTE_PATTERNS = [
    "quote",
    "says:",
    "said:",
    "according to",
]

CULTURAL_QUOTE_PATTERNS = [
    "movie quote",
    "favorite quote",
    "film",
    "scene",
    "character",
    "spielberg",
    "timeless quote",
    "quote comes from",
    "quote about",
]

UNMET_NEED_TERMS = [
    "need",
    "wish",
    "want",
    "looking for",
    "would pay",
    "if only",
    "missing",
    "should support",
    "doesn't support",
]


def score_item_relevance(item: dict) -> dict:
    text = item.get("clean_text", "")
    combined = f"{item.get('title', '')} {text}".lower()
    score = 0
    reasons = []
    penalties = []

    business_hits = _hits(combined, BUSINESS_SCOPE_TERMS)
    if business_hits:
        score += min(9, len(business_hits) * 3)
        reasons.append(f"business_scope_terms:{', '.join(business_hits[:6])}")

    workflow_hits = _hits(combined, WORKFLOW_FRICTION_TERMS)
    if workflow_hits:
        score += min(8, len(workflow_hits) * 2)
        reasons.append(f"workflow_friction_terms:{', '.join(workflow_hits[:6])}")

    practical_tool_hits = _hits(combined, PRACTICAL_TOOL_TERMS)
    if practical_tool_hits:
        score += min(5, len(practical_tool_hits) * 2)
        reasons.append(f"practical_tool_terms:{', '.join(practical_tool_hits[:6])}")

    ai_hits = _hits(combined, AI_OPERATIONAL_TERMS)
    if ai_hits and (business_hits or workflow_hits):
        score += min(3, len(ai_hits))
        reasons.append(f"ai_operational_terms:{', '.join(ai_hits[:4])}")

    adoption_hits = _hits(combined, ADOPTION_RELEVANCE_TERMS)
    if adoption_hits:
        score += min(5, len(adoption_hits))
        reasons.append(f"adoption_terms:{', '.join(adoption_hits[:6])}")

    dissatisfaction_hits = _hits(combined, DISSATISFACTION_RELEVANCE_TERMS)
    if dissatisfaction_hits:
        score += min(4, len(dissatisfaction_hits))
        reasons.append(f"dissatisfaction_terms:{', '.join(dissatisfaction_hits[:6])}")

    if _has_first_person_problem(combined):
        score += 2
        reasons.append("first_person_or_team_problem")

    if item.get("source_type") == "review":
        if workflow_hits or practical_tool_hits or business_hits:
            score += 1
            reasons.append("implementation_feedback_source")

    promo_hits = _hits(combined, PROMOTION_PATTERNS)
    if promo_hits:
        if _has_concrete_operational_pain(combined):
            score -= 4
            penalties.append(f"promotion_with_some_user_pain:{', '.join(promo_hits[:4])}")
        else:
            score -= 11
            penalties.append(f"founder_launch_or_self_promotion:{', '.join(promo_hits[:4])}")

    if _link_drop_density(text):
        score -= 4
        penalties.append("link_drop_density")

    technical_hits = _hits(combined, TECHNICAL_DETAIL_TERMS)
    has_business_context = bool(business_hits or workflow_hits or practical_tool_hits)
    has_concrete_pain = _has_concrete_operational_pain(combined)
    context_anchor_hits = _hits(combined, CONTEXT_ANCHOR_TERMS)
    cultural_hits = _hits(combined, CULTURAL_QUOTE_PATTERNS)

    if cultural_hits:
        if context_anchor_hits:
            score -= 5
            penalties.append(f"cultural_or_quote_reference_with_context:{', '.join(cultural_hits[:4])}")
        else:
            score -= 14
            penalties.append(f"cultural_or_quote_reference_no_operational_context:{', '.join(cultural_hits[:4])}")
    if len(technical_hits) >= 5 and not has_concrete_pain:
        score -= 10
        penalties.append(f"engineering_heavy_weak_venture_context:{', '.join(technical_hits[:6])}")
    elif len(technical_hits) >= 3 and not has_business_context:
        score -= 8
        penalties.append(f"low_level_technical_debugging:{', '.join(technical_hits[:5])}")
    elif len(technical_hits) >= 2 and not (business_hits or workflow_hits):
        score -= 5
        penalties.append(f"api_or_debug_detail_weak_business_context:{', '.join(technical_hits[:5])}")
    elif len(technical_hits) >= 4 and has_business_context and not has_concrete_pain:
        score -= 3
        penalties.append(f"technical_detail_needs_stronger_operational_pain:{', '.join(technical_hits[:5])}")

    generic_hits = _hits(combined, GENERIC_ENTERPRISE_TERMS)
    if generic_hits and not any(term in combined for term in ["small business", "small team", "solo", "workflow", "admin", "crm"]):
        score -= 4
        penalties.append(f"generic_enterprise_weak_scope:{', '.join(generic_hits[:4])}")

    quote_hits = _hits(combined, QUOTE_PATTERNS)
    if quote_hits and not (adoption_hits or dissatisfaction_hits or context_anchor_hits):
        score -= 7
        penalties.append(f"off_topic_or_quote_like:{', '.join(quote_hits[:3])}")

    if not context_anchor_hits:
        score -= 10
        penalties.append("missing_business_workflow_or_tool_context_anchor")
    elif not has_business_context and not adoption_hits and not dissatisfaction_hits:
        score -= 4
        penalties.append("weak_operational_tool_relevance")

    if cultural_hits and not context_anchor_hits:
        exclude_for_relevance = True
    elif not context_anchor_hits:
        exclude_for_relevance = True
    elif item.get("source_type") == "discussion" and not _has_discussion_grade_relevance(combined):
        exclude_for_relevance = True
    elif promo_hits and not has_concrete_pain:
        exclude_for_relevance = True
    elif len(technical_hits) >= 5 and not has_concrete_pain:
        exclude_for_relevance = True
    else:
        exclude_for_relevance = score < 4

    return {
        "relevance_score": score,
        "relevance_reasons": "; ".join(reasons) if reasons else "low_positive_relevance",
        "relevance_penalties": "; ".join(penalties),
        "exclude_for_relevance": exclude_for_relevance,
    }


def score_signal_relevance(row: dict) -> int:
    text = f"{row.get('title', '')} {row.get('evidence_excerpt', '')}".lower()
    category = row.get("category", "")
    score = int(row.get("relevance_score") or 0)

    if category == "adoption_barriers":
        score += 2 * len(_hits(text, ADOPTION_RELEVANCE_TERMS))
        score += 3 * len(_hits(text, ["setup", "onboarding", "integration", "permission", "switching", "migration", "workflow burden", "implementation burden"]))

    if category == "dissatisfaction_current_solutions":
        score += 2 * len(_hits(text, DISSATISFACTION_RELEVANCE_TERMS))
        score += 3 * len(_hits(text, ["poor fit", "too complicated", "complexity", "missing", "manual", "frustrating", "doesn't fit", "fragmented", "slow"]))

    if category == "recurring_problem_signals":
        score += len(_hits(text, BUSINESS_SCOPE_TERMS + WORKFLOW_FRICTION_TERMS))

    if category == "unmet_needs" and not _has_unmet_need_context(text):
        score -= 12

    if _hits(text, PROMOTION_PATTERNS) and not _has_concrete_operational_pain(text):
        score -= 8

    if _hits(text, CULTURAL_QUOTE_PATTERNS) and not _hits(text, CONTEXT_ANCHOR_TERMS):
        score -= 14

    if not _hits(text, CONTEXT_ANCHOR_TERMS):
        score -= 10

    if len(_hits(text, TECHNICAL_DETAIL_TERMS)) >= 3 and not _hits(text, TECHNICAL_CONTEXT_ALLOW_TERMS):
        score -= 8
    elif len(_hits(text, TECHNICAL_DETAIL_TERMS)) >= 5 and not _has_concrete_operational_pain(text):
        score -= 6

    return score


def should_keep_signal(row: dict) -> bool:
    text = f"{row.get('title', '')} {row.get('evidence_excerpt', '')}".lower()
    category = row.get("category", "")
    source_type = row.get("source_type", "")

    if _hits(text, CULTURAL_QUOTE_PATTERNS) and not _hits(text, CONTEXT_ANCHOR_TERMS):
        return False
    if not _hits(text, CONTEXT_ANCHOR_TERMS):
        return False
    if category == "unmet_needs" and not _has_unmet_need_context(text):
        return False
    if source_type == "discussion" and not _has_discussion_grade_relevance(text):
        return False
    if _hits(text, PROMOTION_PATTERNS) and not _has_concrete_operational_pain(text):
        return False
    if len(_hits(text, TECHNICAL_DETAIL_TERMS)) >= 5 and not _has_stackoverflow_grade_context(text):
        return False
    return int(row.get("signal_relevance_score") or 0) >= 4


def summarize_relevance(items: list[dict], excluded: list[dict]) -> dict:
    kept_scores = [item.get("relevance_score", 0) for item in items]
    reason_counts = Counter()
    for item in items:
        for reason in str(item.get("relevance_reasons", "")).split("; "):
            if reason:
                reason_counts[reason.split(":")[0]] += 1
    return {
        "kept_items": len(items),
        "relevance_filtered_items": len(excluded),
        "min_relevance_score": min(kept_scores) if kept_scores else 0,
        "max_relevance_score": max(kept_scores) if kept_scores else 0,
        "top_relevance_reasons": dict(reason_counts.most_common()),
    }


def _hits(text: str, terms: list[str]) -> list[str]:
    hits = []
    for term in terms:
        if _term_in_text(text, term):
            hits.append(term)
    return hits


def _term_in_text(text: str, term: str) -> bool:
    if term == "ai":
        return bool(re.search(r"\bai\b", text))
    if re.fullmatch(r"[a-z0-9]+", term):
        return bool(re.search(rf"\b{re.escape(term)}\b", text))
    return term in text


def _has_first_person_problem(text: str) -> bool:
    actor = any(term in f" {text} " for term in [" i ", " we ", " my ", " our ", " users ", " customers "])
    problem = any(term in text for term in ADOPTION_RELEVANCE_TERMS + DISSATISFACTION_RELEVANCE_TERMS)
    return actor and problem


def _has_concrete_operational_pain(text: str) -> bool:
    scope = _hits(text, BUSINESS_SCOPE_TERMS + WORKFLOW_FRICTION_TERMS + PRACTICAL_TOOL_TERMS)
    pain = _hits(text, ADOPTION_RELEVANCE_TERMS + DISSATISFACTION_RELEVANCE_TERMS)
    user_context = any(term in f" {text} " for term in [" i ", " we ", " my ", " our ", " user ", " users ", " customer ", " customers ", " team ", " business "])
    return bool(scope and pain and user_context)


def _has_unmet_need_context(text: str) -> bool:
    need = _hits(text, UNMET_NEED_TERMS)
    anchor = _hits(text, CONTEXT_ANCHOR_TERMS)
    concrete_tool_or_workflow = _hits(
        text,
        WORKFLOW_FRICTION_TERMS
        + PRACTICAL_TOOL_TERMS
        + [
            "business",
            "customer",
            "client",
            "integration",
            "api",
            "webhook",
            "setup",
            "onboarding",
            "permission",
            "tool",
            "tools",
            "saas",
            "manage",
        ],
    )
    return bool(need and anchor and concrete_tool_or_workflow)


def _has_discussion_grade_relevance(text: str) -> bool:
    if _has_concrete_operational_pain(text) or _has_unmet_need_context(text):
        return True
    anchor = _hits(text, CONTEXT_ANCHOR_TERMS)
    practical_pain = _hits(text, ADOPTION_RELEVANCE_TERMS + DISSATISFACTION_RELEVANCE_TERMS)
    return bool(anchor and practical_pain and _hits(text, WORKFLOW_FRICTION_TERMS + PRACTICAL_TOOL_TERMS))


def _has_stackoverflow_grade_context(text: str) -> bool:
    return bool(
        _hits(text, ["workflow automation", "crm", "saas", "business tool", "customer", "operational data"])
        or (_hits(text, ["webhook", "api", "authentication", "setup", "integration"]) and _hits(text, WORKFLOW_FRICTION_TERMS + PRACTICAL_TOOL_TERMS + BUSINESS_SCOPE_TERMS))
    )


def _link_drop_density(text: str) -> bool:
    urls = re.findall(r"https?://|www\.", text.lower())
    word_count = max(1, len(text.split()))
    return len(urls) >= 2 or (len(urls) == 1 and word_count < 35)
