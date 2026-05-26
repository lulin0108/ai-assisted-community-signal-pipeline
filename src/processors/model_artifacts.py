"""Deterministic model artifact producers."""

from datetime import datetime, timezone
from collections import Counter, defaultdict
import hashlib
import re

from processors.embeddings import EmbeddingProvider, HashingEmbeddingProvider, top_terms


CLASSIFIER_NAME = "heuristic-signal-classifier"
CLASSIFIER_VERSION = "v1"
CLUSTERER_NAME = "heuristic-evidence-clusterer"
CLUSTERER_VERSION = "v2"
CLUSTER_SIMILARITY_THRESHOLD = 0.12


def build_classification_artifacts(items: list[dict], batch_summaries: list[dict]) -> list[dict]:
    artifacts = []
    created_at = datetime.now(timezone.utc).isoformat()
    for item in items:
        artifact = _classify_item(item)
        artifacts.append(
            {
                "batch_index": _batch_index_for_item(item["item_id"], batch_summaries),
                "item_id": item["item_id"],
                "source_id": item["source_id"],
                "artifact_type": "classification",
                "model_name": CLASSIFIER_NAME,
                "model_version": CLASSIFIER_VERSION,
                "input_hash": _input_hash(item),
                "artifact": artifact,
                "created_at": created_at,
            }
        )
    return artifacts


def build_cluster_artifacts(
    items: list[dict],
    batch_summaries: list[dict],
    embedding_provider: EmbeddingProvider | None = None,
    similarity_threshold: float = CLUSTER_SIMILARITY_THRESHOLD,
) -> list[dict]:
    embedding_provider = embedding_provider or HashingEmbeddingProvider()
    grouped = defaultdict(list)
    for item in items:
        grouped[_cluster_key(item)].append(item)

    artifacts = []
    created_at = datetime.now(timezone.utc).isoformat()
    for cluster_key, cluster_items in sorted(grouped.items()):
        components = _embedding_components(cluster_items, embedding_provider, similarity_threshold)
        for component_index, component_items in enumerate(components, start=1):
            component_items = sorted(
                component_items,
                key=lambda item: (-int(item.get("relevance_score", 0)), item["item_id"]),
            )
            cluster_id = _cluster_id(cluster_key, component_index, len(components))
            artifact = _cluster_payload(
                cluster_key,
                cluster_id,
                component_index,
                component_items,
                embedding_provider,
                similarity_threshold,
            )
            artifacts.append(
                {
                    "batch_index": min(_batch_index_for_item(item["item_id"], batch_summaries) for item in component_items),
                    "item_id": artifact["cluster_id"],
                    "source_id": artifact["cluster_id"],
                    "artifact_type": "evidence_cluster",
                    "model_name": CLUSTERER_NAME,
                    "model_version": CLUSTERER_VERSION,
                    "input_hash": _cluster_input_hash(cluster_id, component_items),
                    "artifact": artifact,
                    "created_at": created_at,
                }
            )
    return artifacts


def build_embedding_artifacts(
    items: list[dict],
    batch_summaries: list[dict],
    embedding_provider: EmbeddingProvider | None = None,
) -> list[dict]:
    embedding_provider = embedding_provider or HashingEmbeddingProvider()
    artifacts = []
    created_at = datetime.now(timezone.utc).isoformat()
    for item in items:
        artifact = embedding_provider.payload(item)
        artifacts.append(
            {
                "batch_index": _batch_index_for_item(item["item_id"], batch_summaries),
                "item_id": item["item_id"],
                "source_id": item["source_id"],
                "artifact_type": "embedding",
                "model_name": embedding_provider.artifact_model_name,
                "model_version": embedding_provider.artifact_model_version,
                "input_hash": _input_hash(item),
                "artifact": artifact,
                "created_at": created_at,
            }
        )
    return artifacts


def _classify_item(item: dict) -> dict:
    labels = _labels_from_item(item)
    return {
        "primary_label": labels[0] if labels else "general_signal",
        "labels": labels,
        "relevance_score": item.get("relevance_score", 0),
        "quality_score": item.get("quality_score", 0),
        "relevance_reasons": item.get("relevance_reasons", ""),
        "relevance_penalties": item.get("relevance_penalties", ""),
    }


def _labels_from_item(item: dict) -> list[str]:
    text = " ".join(
        [
            item.get("title", ""),
            item.get("clean_text", ""),
            item.get("relevance_reasons", ""),
        ]
    ).lower()
    labels = []
    checks = [
        ("business_scope", ["business_scope_terms", "small business", "crm", "customer", "admin"]),
        ("workflow_friction", ["workflow_friction_terms", "workflow", "manual", "scattered", "automation"]),
        ("practical_tooling", ["practical_tool_terms", "zapier", "n8n", "airtable", "hubspot", "integration"]),
        ("adoption_barrier", ["adoption_terms", "setup", "onboarding", "permission", "credential", "switching"]),
        ("dissatisfaction", ["dissatisfaction_terms", "frustrating", "fails", "missing", "slow", "broken"]),
        ("ai_operational", ["ai_operational_terms", "ai", "llm", "agent", "assistant"]),
    ]
    for label, terms in checks:
        if any(term in text for term in terms):
            labels.append(label)
    if item.get("source_type") == "review":
        labels.append("implementation_feedback")
    return labels


def _cluster_key(item: dict) -> str:
    text = _item_text(item)
    checks = [
        (
            "customer_data_sync_integration",
            ["crm", "customer", "record", "sync", "field", "api", "integration", "webhook"],
        ),
        (
            "workflow_automation_reliability",
            ["workflow", "automation", "zapier", "n8n", "failed", "fails", "error", "troubleshoot"],
        ),
        (
            "setup_onboarding_credentials",
            ["setup", "onboarding", "credential", "permission", "self-host", "configure"],
        ),
        (
            "admin_fragmentation_manual_work",
            ["admin", "invoice", "scheduling", "follow-up", "scattered", "manual", "operations"],
        ),
        (
            "lean_team_adoption_burden",
            ["small team", "one-person", "solo", "lean team", "without a developer", "maintain"],
        ),
        (
            "ai_trust_accuracy",
            ["ai", "llm", "agent", "assistant", "accuracy", "trust"],
        ),
        (
            "product_complexity_switching_cost",
            ["complicated", "complex", "switching", "migration", "too much", "learning curve"],
        ),
    ]
    scores = [
        (key, sum(1 for term in terms if term in text))
        for key, terms in checks
    ]
    best_key, best_score = max(scores, key=lambda item: item[1])
    if best_score:
        return best_key
    return "general_operational_signal"


def _embedding_components(
    items: list[dict],
    embedding_provider: EmbeddingProvider,
    similarity_threshold: float,
) -> list[list[dict]]:
    items = sorted(items, key=lambda item: item["item_id"])
    vectors = {item["item_id"]: embedding_provider.vector(item) for item in items}
    neighbors = {item["item_id"]: [] for item in items}
    for left_index, left_item in enumerate(items):
        for right_item in items[left_index + 1:]:
            similarity = _cosine(vectors[left_item["item_id"]], vectors[right_item["item_id"]])
            if similarity >= similarity_threshold:
                neighbors[left_item["item_id"]].append(right_item["item_id"])
                neighbors[right_item["item_id"]].append(left_item["item_id"])

    item_by_id = {item["item_id"]: item for item in items}
    seen = set()
    components = []
    for item in items:
        if item["item_id"] in seen:
            continue
        stack = [item["item_id"]]
        component_ids = []
        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            component_ids.append(current)
            stack.extend(neighbors[current])
        components.append([item_by_id[item_id] for item_id in sorted(component_ids)])
    return sorted(
        components,
        key=lambda component: (
            -max(int(item.get("relevance_score", 0)) for item in component),
            component[0]["item_id"],
        ),
    )


def _cluster_payload(
    cluster_key: str,
    cluster_id: str,
    component_index: int,
    items: list[dict],
    embedding_provider: EmbeddingProvider,
    similarity_threshold: float,
) -> dict:
    relevance_scores = [int(item.get("relevance_score", 0)) for item in items]
    source_mix = Counter(item.get("source_type", "") for item in items)
    representative_vector = embedding_provider.vector(items[0])
    return {
        "cluster_id": cluster_id,
        "cluster_key": cluster_key,
        "cluster_index": component_index,
        "label": _cluster_label(cluster_key),
        "product_opportunity": _product_opportunity(cluster_key),
        "item_count": len(items),
        "member_item_ids": [item["item_id"] for item in items],
        "member_source_ids": [item["source_id"] for item in items],
        "representative_item_ids": [item["item_id"] for item in items[:5]],
        "representative_source_ids": [item["source_id"] for item in items[:5]],
        "source_mix": dict(sorted(source_mix.items())),
        "average_relevance_score": round(sum(relevance_scores) / len(relevance_scores), 2),
        "max_relevance_score": max(relevance_scores),
        "top_terms": top_terms(items),
        "evidence_excerpts": [_compact(item.get("clean_text", "")) for item in items[:5]],
        "member_similarity_to_representative": [
            {
                "item_id": item["item_id"],
                "similarity": round(_cosine(representative_vector, embedding_provider.vector(item)), 4),
            }
            for item in items[:10]
        ],
        "similarity_threshold": similarity_threshold,
        "embedding_model": embedding_provider.model_label(),
        "embedding_dimensions": embedding_provider.dimensions(items[0]),
        "grouping_basis": embedding_provider.grouping_basis,
    }


def _cluster_label(cluster_key: str) -> str:
    labels = {
        "customer_data_sync_integration": "Customer data sync and integration reliability pain",
        "workflow_automation_reliability": "Workflow automation reliability and troubleshooting pain",
        "setup_onboarding_credentials": "Setup, onboarding, and credential configuration pain",
        "admin_fragmentation_manual_work": "Admin fragmentation and manual follow-up burden",
        "lean_team_adoption_burden": "Lean-team adoption and maintenance burden",
        "ai_trust_accuracy": "AI trust, accuracy, and operational reliability concern",
        "product_complexity_switching_cost": "Product complexity and switching-cost friction",
        "general_operational_signal": "General operational-tool signal",
    }
    return labels[cluster_key]


def _product_opportunity(cluster_key: str) -> str:
    opportunities = {
        "customer_data_sync_integration": "Reliable sync, field mapping visibility, and recovery workflows.",
        "workflow_automation_reliability": "Automation monitoring, clearer failure states, and easier troubleshooting.",
        "setup_onboarding_credentials": "Simpler setup, credential guidance, and onboarding checkpoints.",
        "admin_fragmentation_manual_work": "Unified admin workflows that reduce repeated manual follow-up.",
        "lean_team_adoption_burden": "Low-maintenance tooling for teams without dedicated operators or developers.",
        "ai_trust_accuracy": "Transparent AI behavior, quality checks, and human review controls.",
        "product_complexity_switching_cost": "Lower-friction migration, simpler defaults, and progressive complexity.",
        "general_operational_signal": "Review source evidence before mapping to a product opportunity.",
    }
    return opportunities[cluster_key]


def _cosine(left: list[float], right: list[float]) -> float:
    return sum(left[index] * right[index] for index in range(len(left)))


def _cluster_id(cluster_key: str, component_index: int, component_count: int) -> str:
    if component_count == 1:
        return f"cluster-{cluster_key}"
    return f"cluster-{cluster_key}-{component_index}"


def _item_text(item: dict) -> str:
    return " ".join(
        [
            item.get("title", ""),
            item.get("clean_text", ""),
            item.get("relevance_reasons", ""),
            item.get("quality_reasons", ""),
        ]
    ).lower()


def _compact(value: str, max_chars: int = 220) -> str:
    text = " ".join(value.split())
    if len(text) <= max_chars:
        return text
    return f"{text[: max_chars - 3]}..."


def _batch_index_for_item(item_id: str, batch_summaries: list[dict]) -> int:
    candidate_index = _item_number(item_id)
    cumulative = 0
    for batch in batch_summaries:
        cumulative += batch["quality_candidates"]
        if candidate_index <= cumulative:
            return batch["batch_index"]
    return batch_summaries[-1]["batch_index"] if batch_summaries else 0


def _item_number(item_id: str) -> int:
    match = re.search(r"-(\d+)$", item_id)
    return int(match.group(1))


def _input_hash(item: dict) -> str:
    value = "\n".join(
        [
            item.get("source_id", ""),
            item.get("title", ""),
            item.get("clean_text", ""),
            str(item.get("relevance_score", "")),
            item.get("relevance_reasons", ""),
            item.get("relevance_penalties", ""),
        ]
    )
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _cluster_input_hash(cluster_key: str, items: list[dict]) -> str:
    value = "\n".join(
        [cluster_key]
        + [
            "|".join(
                [
                    item.get("item_id", ""),
                    item.get("source_id", ""),
                    item.get("title", ""),
                    item.get("clean_text", ""),
                    str(item.get("relevance_score", "")),
                ]
            )
            for item in items
        ]
    )
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
