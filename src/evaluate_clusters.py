"""Evaluate evidence clusters against reviewed source-level labels."""

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from processors.batch_pipeline import process_evidence_batches
from processors.embeddings import build_embedding_provider
from processors.model_artifacts import CLUSTER_SIMILARITY_THRESHOLD, build_cluster_artifacts
from utils.file_utils import write_json


def main(argv: list[str] | None = None) -> None:
    args = build_arg_parser().parse_args(argv)
    thresholds = (
        _parse_thresholds(args.cluster_similarity_thresholds)
        if args.cluster_similarity_thresholds
        else [args.cluster_similarity_threshold]
    )
    if args.embedding_backends:
        result = run_backend_comparison(
            raw_items_file=Path(args.raw_items_file),
            labels_file=Path(args.labels_file),
            backend_specs=_parse_backend_specs(args.embedding_backends, args.embedding_model or ""),
            cluster_similarity_thresholds=thresholds,
            processing_batch_size=args.processing_batch_size,
        )
        rendered = render_backend_comparison(result)
    elif args.cluster_similarity_thresholds:
        result = run_threshold_sweep(
            raw_items_file=Path(args.raw_items_file),
            labels_file=Path(args.labels_file),
            embedding_backend=args.embedding_backend,
            embedding_model=args.embedding_model or "",
            cluster_similarity_thresholds=thresholds,
            processing_batch_size=args.processing_batch_size,
        )
        rendered = render_threshold_sweep(result)
    else:
        result = run_evaluation(
            raw_items_file=Path(args.raw_items_file),
            labels_file=Path(args.labels_file),
            embedding_backend=args.embedding_backend,
            embedding_model=args.embedding_model or "",
            cluster_similarity_threshold=args.cluster_similarity_threshold,
            processing_batch_size=args.processing_batch_size,
        )
        rendered = render_evaluation(result)
    if args.output_json:
        write_json(Path(args.output_json), result)
    if args.output_csv:
        write_evaluation_csv(Path(args.output_csv), result)
    print(rendered)


def run_evaluation(
    raw_items_file: Path,
    labels_file: Path,
    embedding_backend: str,
    embedding_model: str,
    cluster_similarity_threshold: float,
    processing_batch_size: int,
) -> dict[str, Any]:
    raw_items = json.loads(raw_items_file.read_text(encoding="utf-8"))
    labels = json.loads(labels_file.read_text(encoding="utf-8"))
    batch_result = process_evidence_batches(raw_items, processing_batch_size)
    provider = build_embedding_provider(embedding_backend, embedding_model)
    return _evaluate_prepared_items(
        batch_result=batch_result,
        labels=labels,
        embedding_backend=embedding_backend,
        embedding_model=embedding_model,
        cluster_similarity_threshold=cluster_similarity_threshold,
        raw_item_count=len(raw_items),
        provider=provider,
    )


def run_threshold_sweep(
    raw_items_file: Path,
    labels_file: Path,
    embedding_backend: str,
    embedding_model: str,
    cluster_similarity_thresholds: list[float],
    processing_batch_size: int,
) -> dict[str, Any]:
    raw_items = json.loads(raw_items_file.read_text(encoding="utf-8"))
    labels = json.loads(labels_file.read_text(encoding="utf-8"))
    batch_result = process_evidence_batches(raw_items, processing_batch_size)
    provider = build_embedding_provider(embedding_backend, embedding_model)
    results = _threshold_results(
        batch_result=batch_result,
        labels=labels,
        embedding_backend=embedding_backend,
        embedding_model=embedding_model,
        cluster_similarity_thresholds=cluster_similarity_thresholds,
        raw_item_count=len(raw_items),
        provider=provider,
    )
    best_result = _best_result(results)
    return {
        "evaluation_type": "threshold_sweep",
        "embedding_backend": embedding_backend,
        "embedding_model": embedding_model or "default",
        "thresholds": cluster_similarity_thresholds,
        "best_threshold": best_result["cluster_similarity_threshold"],
        "best_pairwise_f1": best_result["pairwise_f1"],
        "results": results,
    }


def run_backend_comparison(
    raw_items_file: Path,
    labels_file: Path,
    backend_specs: list[dict[str, str]],
    cluster_similarity_thresholds: list[float],
    processing_batch_size: int,
) -> dict[str, Any]:
    raw_items = json.loads(raw_items_file.read_text(encoding="utf-8"))
    labels = json.loads(labels_file.read_text(encoding="utf-8"))
    batch_result = process_evidence_batches(raw_items, processing_batch_size)
    backend_results = []
    for spec in backend_specs:
        provider = build_embedding_provider(spec["embedding_backend"], spec["embedding_model"])
        results = _threshold_results(
            batch_result=batch_result,
            labels=labels,
            embedding_backend=spec["embedding_backend"],
            embedding_model=spec["embedding_model"],
            cluster_similarity_thresholds=cluster_similarity_thresholds,
            raw_item_count=len(raw_items),
            provider=provider,
        )
        best_result = _best_result(results)
        backend_results.append(
            {
                "embedding_backend": spec["embedding_backend"],
                "embedding_model": spec["embedding_model"] or "default",
                "best_threshold": best_result["cluster_similarity_threshold"],
                "best_pairwise_f1": best_result["pairwise_f1"],
                "results": results,
            }
        )
    best_backend = max(
        backend_results,
        key=lambda result: (
            result["best_pairwise_f1"],
            _best_result(result["results"])["pairwise_recall"],
            _best_result(result["results"])["pairwise_precision"],
        ),
    )
    return {
        "evaluation_type": "backend_comparison",
        "thresholds": cluster_similarity_thresholds,
        "best_backend": best_backend["embedding_backend"],
        "best_embedding_model": best_backend["embedding_model"],
        "best_threshold": best_backend["best_threshold"],
        "best_pairwise_f1": best_backend["best_pairwise_f1"],
        "backend_results": backend_results,
    }


def _threshold_results(
    batch_result: dict[str, Any],
    labels: dict[str, str],
    embedding_backend: str,
    embedding_model: str,
    cluster_similarity_thresholds: list[float],
    raw_item_count: int,
    provider,
) -> list[dict[str, Any]]:
    return [
        _evaluate_prepared_items(
            batch_result=batch_result,
            labels=labels,
            embedding_backend=embedding_backend,
            embedding_model=embedding_model,
            cluster_similarity_threshold=threshold,
            raw_item_count=raw_item_count,
            provider=provider,
        )
        for threshold in cluster_similarity_thresholds
    ]


def _best_result(results: list[dict[str, Any]]) -> dict[str, Any]:
    return max(
        results,
        key=lambda result: (
            result["pairwise_f1"],
            result["pairwise_recall"],
            result["pairwise_precision"],
            -result["predicted_cluster_count"],
        ),
    )


def _evaluate_prepared_items(
    batch_result: dict[str, Any],
    labels: dict[str, str],
    embedding_backend: str,
    embedding_model: str,
    cluster_similarity_threshold: float,
    raw_item_count: int,
    provider,
) -> dict[str, Any]:
    cluster_artifacts = build_cluster_artifacts(
        batch_result["prepared_items"],
        batch_result["batch_summaries"],
        provider,
        cluster_similarity_threshold,
    )
    return evaluate_cluster_artifacts(
        cluster_artifacts,
        labels,
        embedding_backend=embedding_backend,
        embedding_model=embedding_model or "default",
        cluster_similarity_threshold=cluster_similarity_threshold,
        raw_item_count=raw_item_count,
        prepared_item_count=len(batch_result["prepared_items"]),
    )


def evaluate_cluster_artifacts(
    cluster_artifacts: list[dict],
    labels_by_source_id: dict[str, str],
    embedding_backend: str = "unknown",
    embedding_model: str = "unknown",
    cluster_similarity_threshold: float = CLUSTER_SIMILARITY_THRESHOLD,
    raw_item_count: int = 0,
    prepared_item_count: int = 0,
) -> dict[str, Any]:
    predicted_by_source_id = _predicted_labels(cluster_artifacts)
    source_ids = sorted(set(labels_by_source_id) & set(predicted_by_source_id))
    pair_counts = _pair_counts(source_ids, labels_by_source_id, predicted_by_source_id)
    precision = _ratio(pair_counts["true_positive"], pair_counts["predicted_positive"])
    recall = _ratio(pair_counts["true_positive"], pair_counts["gold_positive"])
    f1 = _ratio(2 * precision * recall, precision + recall)
    return {
        "embedding_backend": embedding_backend,
        "embedding_model": embedding_model,
        "cluster_similarity_threshold": cluster_similarity_threshold,
        "raw_item_count": raw_item_count,
        "prepared_item_count": prepared_item_count,
        "labeled_item_count": len(source_ids),
        "predicted_cluster_count": len(cluster_artifacts),
        "pairwise_precision": round(precision, 4),
        "pairwise_recall": round(recall, 4),
        "pairwise_f1": round(f1, 4),
        "pair_counts": pair_counts,
        "missing_labeled_source_ids": sorted(set(labels_by_source_id) - set(predicted_by_source_id)),
        "clusters": _cluster_rows(cluster_artifacts),
    }


def render_evaluation(result: dict[str, Any]) -> str:
    lines = [
        "Cluster Evaluation",
        f"embedding_backend: {result['embedding_backend']}",
        f"embedding_model: {result['embedding_model']}",
        f"cluster_similarity_threshold: {result['cluster_similarity_threshold']}",
        f"items: raw={result['raw_item_count']}, prepared={result['prepared_item_count']}, labeled={result['labeled_item_count']}",
        f"predicted_clusters: {result['predicted_cluster_count']}",
        (
            "pairwise: "
            f"precision={result['pairwise_precision']}, "
            f"recall={result['pairwise_recall']}, "
            f"f1={result['pairwise_f1']}"
        ),
    ]
    if result["missing_labeled_source_ids"]:
        lines.append(f"missing_labeled_source_ids: {', '.join(result['missing_labeled_source_ids'])}")
    lines.append("clusters:")
    for cluster in result["clusters"]:
        lines.append(
            f"- {cluster['cluster_id']} | key={cluster['cluster_key']} | "
            f"items={cluster['item_count']} | source_ids={', '.join(cluster['source_ids'])}"
        )
    return "\n".join(lines)


def render_threshold_sweep(result: dict[str, Any]) -> str:
    lines = [
        "Cluster Threshold Sweep",
        f"embedding_backend: {result['embedding_backend']}",
        f"embedding_model: {result['embedding_model']}",
        f"best_threshold: {result['best_threshold']}",
        f"best_pairwise_f1: {result['best_pairwise_f1']}",
        "thresholds:",
    ]
    for item in result["results"]:
        lines.append(
            (
                f"- threshold={item['cluster_similarity_threshold']} | "
                f"clusters={item['predicted_cluster_count']} | "
                f"precision={item['pairwise_precision']} | "
                f"recall={item['pairwise_recall']} | "
                f"f1={item['pairwise_f1']}"
            )
        )
    return "\n".join(lines)


def render_backend_comparison(result: dict[str, Any]) -> str:
    lines = [
        "Cluster Backend Comparison",
        f"best_backend: {result['best_backend']}",
        f"best_embedding_model: {result['best_embedding_model']}",
        f"best_threshold: {result['best_threshold']}",
        f"best_pairwise_f1: {result['best_pairwise_f1']}",
        "backends:",
    ]
    for backend_result in result["backend_results"]:
        lines.append(
            (
                f"- backend={backend_result['embedding_backend']} | "
                f"model={backend_result['embedding_model']} | "
                f"best_threshold={backend_result['best_threshold']} | "
                f"best_f1={backend_result['best_pairwise_f1']}"
            )
        )
        for item in backend_result["results"]:
            lines.append(
                (
                    f"  threshold={item['cluster_similarity_threshold']} | "
                    f"clusters={item['predicted_cluster_count']} | "
                    f"precision={item['pairwise_precision']} | "
                    f"recall={item['pairwise_recall']} | "
                    f"f1={item['pairwise_f1']}"
                )
            )
    return "\n".join(lines)


def write_evaluation_csv(path: Path, result: dict[str, Any]) -> None:
    rows = evaluation_rows(result)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_threshold_sweep_csv(path: Path, result: dict[str, Any]) -> None:
    write_evaluation_csv(path, result)


def evaluation_rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    if result.get("evaluation_type") == "backend_comparison":
        rows = []
        for backend_result in result["backend_results"]:
            rows.extend(threshold_sweep_rows(backend_result))
        return rows
    if "results" in result:
        return threshold_sweep_rows(result)
    return [_evaluation_row(result)]


def threshold_sweep_rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    return [_evaluation_row(item) for item in result.get("results", [])]


def _evaluation_row(result: dict[str, Any]) -> dict[str, Any]:
    pair_counts = result["pair_counts"]
    return {
        "embedding_backend": result["embedding_backend"],
        "embedding_model": result["embedding_model"],
        "cluster_similarity_threshold": result["cluster_similarity_threshold"],
        "predicted_cluster_count": result["predicted_cluster_count"],
        "labeled_item_count": result["labeled_item_count"],
        "pairwise_precision": result["pairwise_precision"],
        "pairwise_recall": result["pairwise_recall"],
        "pairwise_f1": result["pairwise_f1"],
        "true_positive_pairs": pair_counts["true_positive"],
        "predicted_positive_pairs": pair_counts["predicted_positive"],
        "gold_positive_pairs": pair_counts["gold_positive"],
        "pair_count": pair_counts["pair_count"],
    }


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Evaluate evidence cluster assignments.")
    parser.add_argument(
        "--raw-items-file",
        default="samples/small_business_operations_raw_items.json",
        help="Path to a JSON list of raw items.",
    )
    parser.add_argument(
        "--labels-file",
        default="samples/cluster_review_labels.json",
        help="Path to source_id to reviewed cluster label JSON.",
    )
    parser.add_argument(
        "--embedding-backend",
        choices=["hashing", "sentence-transformer"],
        default="hashing",
        help="Embedding backend used for cluster similarity.",
    )
    parser.add_argument(
        "--embedding-backends",
        help="Semicolon-separated backend specs for comparison, such as hashing;sentence-transformer:sentence-transformers/all-MiniLM-L6-v2.",
    )
    parser.add_argument(
        "--embedding-model",
        default="",
        help="Sentence-transformer model identifier when using the sentence-transformer backend.",
    )
    parser.add_argument(
        "--cluster-similarity-threshold",
        type=float,
        default=CLUSTER_SIMILARITY_THRESHOLD,
        help="Cosine similarity threshold inside each pain-mechanism bucket.",
    )
    parser.add_argument(
        "--cluster-similarity-thresholds",
        help="Semicolon-separated thresholds for comparison, such as 0.05;0.12;0.2.",
    )
    parser.add_argument(
        "--processing-batch-size",
        type=int,
        default=500,
        help="Raw items per filtering and relevance batch.",
    )
    parser.add_argument(
        "--output-json",
        help="Optional path for writing the evaluation result JSON.",
    )
    parser.add_argument(
        "--output-csv",
        help="Optional CSV path for threshold sweep summary rows.",
    )
    return parser


def _predicted_labels(cluster_artifacts: list[dict]) -> dict[str, str]:
    labels = {}
    for artifact in cluster_artifacts:
        cluster = artifact["artifact"]
        for source_id in cluster.get("member_source_ids", cluster["representative_source_ids"]):
            labels[source_id] = cluster["cluster_id"]
    return labels


def _pair_counts(
    source_ids: list[str],
    labels_by_source_id: dict[str, str],
    predicted_by_source_id: dict[str, str],
) -> dict[str, int]:
    counts = {
        "true_positive": 0,
        "predicted_positive": 0,
        "gold_positive": 0,
        "pair_count": 0,
    }
    for left_index, left_id in enumerate(source_ids):
        for right_id in source_ids[left_index + 1:]:
            same_gold = labels_by_source_id[left_id] == labels_by_source_id[right_id]
            same_predicted = predicted_by_source_id[left_id] == predicted_by_source_id[right_id]
            counts["pair_count"] += 1
            if same_gold:
                counts["gold_positive"] += 1
            if same_predicted:
                counts["predicted_positive"] += 1
            if same_gold and same_predicted:
                counts["true_positive"] += 1
    return counts


def _cluster_rows(cluster_artifacts: list[dict]) -> list[dict[str, Any]]:
    rows = []
    for artifact in cluster_artifacts:
        cluster = artifact["artifact"]
        rows.append(
            {
                "cluster_id": cluster["cluster_id"],
                "cluster_key": cluster["cluster_key"],
                "item_count": cluster["item_count"],
                "source_ids": cluster.get("member_source_ids", cluster["representative_source_ids"]),
                "top_terms": cluster["top_terms"],
            }
        )
    return rows


def _ratio(numerator: float, denominator: float) -> float:
    if not denominator:
        return 0.0
    return numerator / denominator


def _parse_thresholds(value: str) -> list[float]:
    return [float(item.strip()) for item in value.split(";") if item.strip()]


def _parse_backend_specs(value: str, default_model: str) -> list[dict[str, str]]:
    specs = []
    for item in value.split(";"):
        item = item.strip()
        if not item:
            continue
        if ":" in item:
            backend, model = item.split(":", 1)
        else:
            backend, model = item, default_model
        specs.append(
            {
                "embedding_backend": backend.strip(),
                "embedding_model": model.strip(),
            }
        )
    return specs


if __name__ == "__main__":
    main()
