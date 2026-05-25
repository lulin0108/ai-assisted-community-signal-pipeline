"""CSV exports for evidence and summaries."""

import csv
from pathlib import Path


def export_csv_outputs(
    analysis: dict,
    items: list[dict],
    output_dir: Path,
    run_id: str,
    excluded_items: list[dict] | None = None,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    evidence_path = output_dir / f"{run_id}_evidence_items.csv"
    items_path = output_dir / f"{run_id}_normalized_items.csv"
    summary_path = output_dir / f"{run_id}_section_summary.csv"
    excluded_path = output_dir / f"{run_id}_excluded_items.csv"

    _write_rows(evidence_path, analysis["evidence_rows"])
    _write_rows(items_path, items)
    _write_rows(summary_path, _summary_rows(analysis))
    _write_rows(excluded_path, excluded_items or [])

    return {
        "evidence_csv": evidence_path,
        "items_csv": items_path,
        "summary_csv": summary_path,
        "excluded_csv": excluded_path,
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
