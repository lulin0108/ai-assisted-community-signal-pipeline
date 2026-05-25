"""CSV exports for evidence and summaries."""

import csv
from pathlib import Path


def export_csv_outputs(
    analysis: dict,
    items: list[dict],
    output_dir: Path,
    run_id: str,
    excluded_items: list[dict] | None = None,
    cluster_artifacts: list[dict] | None = None,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    evidence_path = output_dir / f"{run_id}_evidence_items.csv"
    items_path = output_dir / f"{run_id}_normalized_items.csv"
    summary_path = output_dir / f"{run_id}_section_summary.csv"
    excluded_path = output_dir / f"{run_id}_excluded_items.csv"
    clusters_path = output_dir / f"{run_id}_evidence_clusters.csv"

    _write_rows(evidence_path, analysis["evidence_rows"])
    _write_rows(items_path, items)
    _write_rows(summary_path, _summary_rows(analysis))
    _write_rows(excluded_path, excluded_items or [])
    _write_rows(clusters_path, _cluster_rows(cluster_artifacts or []))

    return {
        "evidence_csv": evidence_path,
        "items_csv": items_path,
        "summary_csv": summary_path,
        "excluded_csv": excluded_path,
        "clusters_csv": clusters_path,
    }


def _write_rows(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return

    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _summary_rows(analysis: dict) -> list[dict]:
    rows = []
    for category, summary in analysis["category_summaries"].items():
        rows.append(
            {
                "category": category,
                "title": summary["title"],
                "evidence_count": summary["evidence_count"],
                "discussion_count": summary["discussion_count"],
                "review_count": summary["review_count"],
                "top_terms": ", ".join(summary["top_terms"]),
                "summary": summary["summary"],
            }
        )
    return rows


def _cluster_rows(cluster_artifacts: list[dict]) -> list[dict]:
    rows = []
    for artifact in cluster_artifacts:
        cluster = artifact["artifact"]
        rows.append(
            {
                "cluster_id": cluster["cluster_id"],
                "cluster_key": cluster["cluster_key"],
                "label": cluster["label"],
                "product_opportunity": cluster["product_opportunity"],
                "item_count": cluster["item_count"],
                "source_mix": _format_dict(cluster.get("source_mix", {})),
                "average_relevance_score": cluster.get("average_relevance_score", ""),
                "max_relevance_score": cluster.get("max_relevance_score", ""),
                "top_terms": ", ".join(cluster.get("top_terms", [])),
                "representative_item_ids": ", ".join(cluster.get("representative_item_ids", [])),
                "representative_source_ids": ", ".join(cluster.get("representative_source_ids", [])),
                "grouping_basis": cluster.get("grouping_basis", ""),
                "embedding_model": cluster.get("embedding_model", ""),
                "similarity_threshold": cluster.get("similarity_threshold", ""),
            }
        )
    return rows


def _format_dict(value: dict) -> str:
    if not value:
        return "none"
    return ", ".join(f"{key}={count}" for key, count in value.items())
