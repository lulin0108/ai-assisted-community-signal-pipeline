"""Inspect stored pipeline runs from the local SQLite index."""

import argparse
from pathlib import Path
from typing import Any

from config import ROOT_DIR
from storage.sqlite_store import (
    get_cluster_artifacts,
    get_collection_states,
    get_embedding_artifacts,
    get_evidence_rows,
    get_model_artifacts,
    get_processing_batches,
    get_run_chain_cluster_artifacts,
    get_run_chain_embedding_artifacts,
    get_run_chain_evidence_rows,
    get_run_chain_model_artifacts,
    get_run_chain_summary,
    get_run_summary,
    list_runs,
)


DEFAULT_DB_PATH = ROOT_DIR / "data" / "storage" / "pipeline_runs.sqlite3"


def main(argv: list[str] | None = None) -> None:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    db_path = Path(args.db_path)

    if args.collection_state and not args.run_id:
        parser.error("--collection-state requires --run-id")
    if args.evidence and not args.run_id:
        parser.error("--evidence requires --run-id")
    if args.batches and not args.run_id:
        parser.error("--batches requires --run-id")
    if args.artifacts and not args.run_id:
        parser.error("--artifacts requires --run-id")
    if args.clusters and not args.run_id:
        parser.error("--clusters requires --run-id")
    if args.embeddings and not args.run_id:
        parser.error("--embeddings requires --run-id")
    if args.chain and not args.run_id:
        parser.error("--chain requires --run-id")

    if args.list or not args.run_id:
        print(render_run_list(list_runs(db_path, limit=args.limit, offset=args.offset)))
        return

    summary = get_run_summary(db_path, args.run_id)
    if summary is None:
        raise SystemExit(f"Run not found: {args.run_id}")

    sections = [render_run_summary(summary)]
    if args.chain:
        chain_summary = get_run_chain_summary(db_path, args.run_id)
        if chain_summary is None:
            raise SystemExit(f"Run chain not found: {args.run_id}")
        sections.append(render_run_chain_summary(chain_summary))
    if args.collection_state:
        sections.append(render_collection_states(get_collection_states(db_path, args.run_id)))
    if args.batches:
        sections.append(render_processing_batches(get_processing_batches(db_path, args.run_id)))
    if args.artifacts:
        artifact_reader = get_run_chain_model_artifacts if args.chain else get_model_artifacts
        sections.append(
            render_model_artifacts(
                artifact_reader(
                    db_path,
                    args.run_id,
                    artifact_type=args.artifact_type,
                    batch_index=args.batch_index,
                    limit=args.limit,
                    offset=args.offset,
                )
            )
        )
    if args.clusters:
        cluster_reader = get_run_chain_cluster_artifacts if args.chain else get_cluster_artifacts
        sections.append(
            render_cluster_artifacts(
                cluster_reader(
                    db_path,
                    args.run_id,
                    limit=args.limit,
                    offset=args.offset,
                )
            )
        )
    if args.embeddings:
        embedding_reader = get_run_chain_embedding_artifacts if args.chain else get_embedding_artifacts
        sections.append(
            render_embedding_artifacts(
                embedding_reader(
                    db_path,
                    args.run_id,
                    limit=args.limit,
                    offset=args.offset,
                )
            )
        )
    if args.evidence:
        evidence_reader = get_run_chain_evidence_rows if args.chain else get_evidence_rows
        sections.append(
            render_evidence_rows(
                evidence_reader(
                    db_path,
                    args.run_id,
                    limit=args.limit,
                    offset=args.offset,
                    category=args.category,
                )
            )
        )
    print("\n\n".join(sections))


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect stored pipeline runs.")
    target = parser.add_mutually_exclusive_group()
    target.add_argument("--list", action="store_true", help="List stored runs.")
    target.add_argument("--run-id", help="Inspect one stored run.")
    parser.add_argument("--db-path", default=str(DEFAULT_DB_PATH), help="Path to the SQLite run index.")
    parser.add_argument("--collection-state", action="store_true", help="Show per-source/query collection state.")
    parser.add_argument("--chain", action="store_true", help="Show aggregate counts across this run's resume chain.")
    parser.add_argument("--batches", action="store_true", help="Show processing batch records.")
    parser.add_argument("--artifacts", action="store_true", help="Show stored model artifacts.")
    parser.add_argument("--clusters", action="store_true", help="Show evidence cluster artifacts.")
    parser.add_argument("--embeddings", action="store_true", help="Show text embedding artifacts.")
    parser.add_argument("--artifact-type", help="Filter model artifacts by type.")
    parser.add_argument("--batch-index", type=int, help="Filter model artifacts by batch index.")
    parser.add_argument("--evidence", action="store_true", help="Show ranked evidence rows.")
    parser.add_argument("--category", help="Filter evidence rows by category.")
    parser.add_argument("--limit", type=int, default=10, help="Maximum rows to show.")
    parser.add_argument("--offset", type=int, default=0, help="Rows to skip.")
    return parser


def render_run_list(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "No runs found."

    lines = ["Runs"]
    for row in rows:
        lines.append(
            (
                f"- {row['run_id']} | {row['generated_at_utc']} | "
                f"items={row['total_items_analyzed']} | evidence={row['evidence_rows']} | "
                f"fallback={row['demo_fallback_items']} | theme={row['venture_category']}"
            )
        )
    return "\n".join(lines)


def render_run_summary(summary: dict[str, Any]) -> str:
    lines = [
        f"Run {summary['run_id']}",
        f"generated_at_utc: {summary['generated_at_utc']}",
        f"venture_category: {summary['venture_category']}",
        f"community_queries: {_join(summary['community_queries'])}",
        f"stackexchange_site: {summary['stackexchange_site']}",
        f"stackexchange_queries: {_join(summary['stackexchange_queries'])}",
        (
            "limits: "
            f"discussion={summary['max_discussion_items']}, "
            f"review={summary['max_review_items']}, "
            f"timeout={summary['request_timeout']}, "
            f"batch={summary['processing_batch_size']}"
        ),
        f"collection_policy: {_format_counts(summary['collection_policy'])}",
        f"raw_items_file: {summary['raw_items_file'] or '(live collectors)'}",
        f"resume_from_run_id: {summary['resume_from_run_id'] or '(none)'}",
        (
            "volume: "
            f"items={summary['total_items_analyzed']}, "
            f"evidence={summary['evidence_rows']}, "
            f"fallback={summary['demo_fallback_items']}"
        ),
        "sources:",
    ]
    for key, diagnostics in summary["collector_diagnostics"].items():
        live_count = diagnostics.get("live_items_fetched_count", diagnostics.get("live_question_count_fetched", 0))
        failure = diagnostics.get("failure_type", "")
        lines.append(
            f"- {key}: source={diagnostics.get('source', '')}, live={live_count}, "
            f"fallback={diagnostics.get('fallback_triggered', False)}, failure={failure or '(none)'}"
        )

    lines.append("categories:")
    for category, category_summary in summary["category_summaries"].items():
        lines.append(f"- {category}: evidence={category_summary['evidence_count']}")
    return "\n".join(lines)


def render_collection_states(states: list[dict[str, Any]]) -> str:
    if not states:
        return "Collection State\nNo collection state rows."

    lines = ["Collection State"]
    for state in states:
        completed = "yes" if state["completed"] else "no"
        lines.append(
            (
                f"- {state['source']} | {state['query']} | pages={state['page_count']} | "
                f"last={state['last_page_number']} | next={state['next_page_number']} | "
                f"raw={state['total_raw_count']} | items={state['total_item_count']} | completed={completed}"
            )
        )
    return "\n".join(lines)


def render_run_chain_summary(summary: dict[str, Any]) -> str:
    storage = summary["storage_counts"]
    run_volume = summary["run_volume"]
    lines = [
        "Run Chain",
        f"latest_run_id: {summary['latest_run_id']}",
        f"root_run_id: {summary['root_run_id']}",
        f"run_count: {summary['run_count']}",
        f"run_ids: {_join(summary['run_ids'])}",
        f"generated_at_utc: {summary['generated_at_utc_start']} -> {summary['generated_at_utc_end']}",
        f"venture_categories: {_join(summary['venture_categories'])}",
        (
            "run_volume: "
            f"items={run_volume['total_items_analyzed']}, "
            f"evidence={run_volume['evidence_rows']}, "
            f"fallback={run_volume['demo_fallback_items']}"
        ),
        (
            "storage_counts: "
            f"raw={storage['raw_items']}, "
            f"unique_raw={storage['unique_raw_items']}, "
            f"prepared={storage['prepared_items']}, "
            f"excluded={storage['excluded_items']}, "
            f"relevance_excluded={storage['relevance_excluded_items']}, "
            f"evidence={storage['evidence_rows']}, "
            f"pages={storage['collection_pages']}, "
            f"batches={storage['processing_batches']}, "
            f"artifacts={storage['model_artifacts']}"
        ),
        f"batch_status: {_format_counts(summary['processing_batches_by_status'])}",
        f"artifact_types: {_format_counts(summary['model_artifacts_by_type'])}",
        (
            "collection_states: "
            f"completed={summary['collection_states']['completed']}, "
            f"open={summary['collection_states']['open']}"
        ),
    ]
    if summary["resume_links"]:
        lines.append("resume_links:")
        for child, parent in summary["resume_links"].items():
            lines.append(f"- {child} <- {parent}")
    return "\n".join(lines)


def render_evidence_rows(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "Evidence Rows\nNo evidence rows."

    lines = ["Evidence Rows"]
    for row in rows:
        run_prefix = f"run={row['run_id']} | " if "run_id" in row else ""
        lines.append(
            (
                f"- [{row['signal_relevance_score']}] {run_prefix}{row['category']} | "
                f"{row['source_type']}:{row.get('source_id', '')} | {row['title']}"
            )
        )
        lines.append(f"  {_compact(row['evidence_excerpt'])}")
    return "\n".join(lines)


def render_processing_batches(batches: list[dict[str, Any]]) -> str:
    if not batches:
        return "Processing Batches\nNo processing batch rows."

    lines = ["Processing Batches"]
    for batch in batches:
        lines.append(
            (
                f"- batch={batch['batch_index']} | status={batch['status']} | "
                f"raw_range={batch['raw_item_start_index']}-{batch['raw_item_end_index']} | "
                f"raw={batch['raw_items']} | quality_candidates={batch['quality_candidates']} | "
                f"quality_excluded={batch['quality_excluded']} | "
                f"relevance_prepared={batch['relevance_prepared']} | "
                f"relevance_excluded={batch['relevance_excluded']}"
            )
        )
    return "\n".join(lines)


def render_model_artifacts(artifacts: list[dict[str, Any]]) -> str:
    if not artifacts:
        return "Model Artifacts\nNo model artifact rows."

    lines = ["Model Artifacts"]
    for artifact in artifacts:
        run_prefix = f"run={artifact['run_id']} | " if "run_id" in artifact else ""
        lines.append(
            (
                f"- {run_prefix}batch={artifact['batch_index']} | item={artifact['item_id']} | "
                f"type={artifact['artifact_type']} | model={artifact['model_name']}@{artifact['model_version']} | "
                f"source_id={artifact['source_id']} | input_hash={artifact['input_hash']}"
            )
        )
        lines.append(f"  {_compact(str(artifact['artifact']))}")
    return "\n".join(lines)


def render_cluster_artifacts(artifacts: list[dict[str, Any]]) -> str:
    if not artifacts:
        return "Evidence Clusters\nNo evidence cluster artifacts."

    lines = ["Evidence Clusters"]
    for artifact in artifacts:
        payload = artifact["artifact"]
        run_prefix = f"run={artifact['run_id']} | " if "run_id" in artifact else ""
        lines.append(
            (
                f"- {run_prefix}{payload['cluster_id']} | items={payload['item_count']} | "
                f"avg_relevance={payload['average_relevance_score']} | {payload['label']}"
            )
        )
        lines.append(f"  opportunity: {payload['product_opportunity']}")
        lines.append(
            f"  basis: {payload.get('grouping_basis', '')}; threshold={payload.get('similarity_threshold', '')}"
        )
        lines.append(f"  terms: {_join(payload['top_terms'])}")
        lines.append(f"  representatives: {_join(payload['representative_item_ids'])}")
    return "\n".join(lines)


def render_embedding_artifacts(artifacts: list[dict[str, Any]]) -> str:
    if not artifacts:
        return "Embedding Artifacts\nNo embedding artifacts."

    lines = ["Embedding Artifacts"]
    for artifact in artifacts:
        payload = artifact["artifact"]
        run_prefix = f"run={artifact['run_id']} | " if "run_id" in artifact else ""
        stored_values = payload.get("nonzero_indices", payload.get("values", []))
        lines.append(
            (
                f"- {run_prefix}item={artifact['item_id']} | model={artifact['model_name']}@{artifact['model_version']} | "
                f"dims={payload['dimensions']} | stored_values={len(stored_values)} | tokens={payload['token_count']}"
            )
        )
        lines.append(f"  terms: {_join(payload['top_terms'])}")
    return "\n".join(lines)


def _join(values: list[str]) -> str:
    return "; ".join(values)


def _compact(value: str, max_chars: int = 160) -> str:
    text = " ".join(value.split())
    if len(text) <= max_chars:
        return text
    return f"{text[: max_chars - 3]}..."


def _format_counts(counts: dict[str, Any]) -> str:
    if not counts:
        return "(none)"
    return ", ".join(f"{key}={value}" for key, value in counts.items())


if __name__ == "__main__":
    main()
