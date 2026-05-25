"""Export cluster review files for human labeling."""

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from config import ROOT_DIR
from utils.file_utils import write_json


def main(argv: list[str] | None = None) -> None:
    args = build_arg_parser().parse_args(argv)
    cluster_path, items_path = _input_paths(args)
    rows = build_review_rows(
        json.loads(cluster_path.read_text(encoding="utf-8")),
        json.loads(items_path.read_text(encoding="utf-8")),
    )
    output_csv = Path(args.output_csv) if args.output_csv else ROOT_DIR / "output" / "csv" / f"{args.run_id}_cluster_review.csv"
    output_labels = (
        Path(args.output_labels_json)
        if args.output_labels_json
        else ROOT_DIR / "output" / "csv" / f"{args.run_id}_cluster_review_labels.json"
    )
    write_review_csv(output_csv, rows)
    write_json(output_labels, build_label_template(rows))
    print(render_export_summary(rows, output_csv, output_labels))


def build_review_rows(cluster_artifacts: list[dict], prepared_items: list[dict]) -> list[dict[str, Any]]:
    item_by_id = {item["item_id"]: item for item in prepared_items}
    rows = []
    for artifact in cluster_artifacts:
        cluster = artifact["artifact"]
        for item_id in cluster.get("member_item_ids", cluster["representative_item_ids"]):
            item = item_by_id[item_id]
            rows.append(
                {
                    "source_id": item["source_id"],
                    "item_id": item["item_id"],
                    "current_cluster_id": cluster["cluster_id"],
                    "current_cluster_key": cluster["cluster_key"],
                    "reviewed_cluster_label": cluster["cluster_key"],
                    "source_type": item["source_type"],
                    "source_name": item["source_name"],
                    "title": item["title"],
                    "relevance_score": item.get("relevance_score", ""),
                    "source_url": item["source_url"],
                    "top_terms": ", ".join(cluster.get("top_terms", [])),
                    "text_excerpt": _compact(item.get("clean_text", "")),
                }
            )
    return sorted(rows, key=lambda row: (row["current_cluster_key"], row["source_id"]))


def build_label_template(rows: list[dict[str, Any]]) -> dict[str, str]:
    return {row["source_id"]: row["reviewed_cluster_label"] for row in rows}


def write_review_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def render_export_summary(rows: list[dict[str, Any]], output_csv: Path, output_labels: Path) -> str:
    cluster_ids = {row["current_cluster_id"] for row in rows}
    return "\n".join(
        [
            "Cluster Review Export",
            f"rows: {len(rows)}",
            f"clusters: {len(cluster_ids)}",
            f"csv: {output_csv}",
            f"labels_json: {output_labels}",
        ]
    )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Export cluster review CSV and label template JSON.")
    parser.add_argument("--run-id", required=True, help="Run ID used to locate processed artifacts or name outputs.")
    parser.add_argument("--cluster-artifacts-file", help="Path to <run_id>_cluster_artifacts.json.")
    parser.add_argument("--prepared-items-file", help="Path to <run_id>_normalized_items.json.")
    parser.add_argument("--output-csv", help="Output CSV path for human review.")
    parser.add_argument("--output-labels-json", help="Output source_id to label JSON template path.")
    return parser


def _input_paths(args: argparse.Namespace) -> tuple[Path, Path]:
    cluster_path = (
        Path(args.cluster_artifacts_file)
        if args.cluster_artifacts_file
        else ROOT_DIR / "data" / "processed" / f"{args.run_id}_cluster_artifacts.json"
    )
    items_path = (
        Path(args.prepared_items_file)
        if args.prepared_items_file
        else ROOT_DIR / "data" / "processed" / f"{args.run_id}_normalized_items.json"
    )
    return cluster_path, items_path


def _compact(value: str, max_chars: int = 320) -> str:
    text = " ".join(value.split())
    if len(text) <= max_chars:
        return text
    return f"{text[: max_chars - 3]}..."


if __name__ == "__main__":
    main()
