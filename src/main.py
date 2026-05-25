"""Run the end-to-end venture signal pipeline."""

import json
import logging
from pathlib import Path

from analyzers.venture_signal_analyzer import analyze_venture_signals
from collectors.source1_collector import collect_discussion_items
from collectors.source2_collector import collect_review_items
from config import PipelineConfig
from exporters.csv_exporter import export_csv_outputs
from exporters.html_exporter import export_html_report
from exporters.markdown_exporter import export_markdown_report
from models import CollectorDiagnostics
from processors.batch_pipeline import process_evidence_batches
from processors.embeddings import build_embedding_provider
from processors.model_artifacts import build_classification_artifacts, build_cluster_artifacts, build_embedding_artifacts
from storage.sqlite_store import (
    get_raw_item_source_keys,
    get_resume_lineage_run_ids,
    get_resume_start_pages,
    save_model_artifacts,
    save_run_to_sqlite,
)
from utils.file_utils import ensure_directories, make_run_id, write_json


logger = logging.getLogger(__name__)


def main() -> None:
    _configure_logging()
    config = PipelineConfig.from_args()
    ensure_directories(
        [
            config.raw_dir,
            config.processed_dir,
            config.storage_dir,
            config.csv_dir,
            config.markdown_dir,
            config.html_dir,
        ]
    )

    run_id = make_run_id()

    if config.raw_items_file:
        raw_items = _load_raw_items(config.raw_items_file)
        source1_diagnostics, source2_diagnostics = _local_file_diagnostics(config, raw_items)
    else:
        source1_start_pages, source2_start_pages = _resume_start_pages(config)
        if config.enable_discussion_source:
            discussion_items, source1_diagnostics = collect_discussion_items(config, source1_start_pages)
        else:
            discussion_items, source1_diagnostics = [], _disabled_source_diagnostics(config, "source1")
        if config.enable_review_source:
            review_items, source2_diagnostics = collect_review_items(config, source2_start_pages)
        else:
            review_items, source2_diagnostics = [], _disabled_source_diagnostics(config, "source2")
        raw_items = discussion_items + review_items
    raw_items, cross_run_duplicate_items = _dedupe_resume_raw_items(config, raw_items)
    write_json(config.raw_dir / f"{run_id}_raw_items.json", raw_items)

    collector_diagnostics = {
        "source1": source1_diagnostics,
        "source2": source2_diagnostics,
        "final_fallback_item_count": sum(1 for item in raw_items if item.get("is_demo_fallback")),
        "debug_save_raw": config.debug_save_raw,
        "raw_items_file": config.raw_items_file,
        "resume_from_run_id": config.resume_from_run_id,
        "cross_run_duplicate_items": len(cross_run_duplicate_items),
    }
    collector_diagnostics_path = config.raw_dir / f"{run_id}_collector_diagnostics.json"
    write_json(collector_diagnostics_path, collector_diagnostics)

    batch_result = process_evidence_batches(raw_items, config.processing_batch_size)
    candidate_items = batch_result["candidate_items"]
    excluded_items = batch_result["excluded_items"]
    filtering_summary = batch_result["filtering_summary"]
    prepared_items = batch_result["prepared_items"]
    relevance_excluded_items = batch_result["relevance_excluded_items"]
    relevance_summary = batch_result["relevance_summary"]
    filtering_summary_path = config.processed_dir / f"{run_id}_filtering_summary.json"
    excluded_items_path = config.processed_dir / f"{run_id}_excluded_items.json"
    cross_run_duplicate_path = config.processed_dir / f"{run_id}_cross_run_duplicate_items.json"
    batch_summary_path = config.processed_dir / f"{run_id}_batch_summary.json"
    write_json(filtering_summary_path, filtering_summary)
    write_json(excluded_items_path, excluded_items)
    write_json(cross_run_duplicate_path, cross_run_duplicate_items)
    write_json(batch_summary_path, batch_result["batch_summaries"])

    relevance_excluded_path = config.processed_dir / f"{run_id}_relevance_excluded_items.json"
    write_json(config.processed_dir / f"{run_id}_normalized_items.json", prepared_items)
    write_json(relevance_excluded_path, relevance_excluded_items)

    embedding_provider = build_embedding_provider(config.embedding_backend, config.embedding_model)
    classification_artifacts = build_classification_artifacts(prepared_items, batch_result["batch_summaries"])
    embedding_artifacts = build_embedding_artifacts(prepared_items, batch_result["batch_summaries"], embedding_provider)
    cluster_artifacts = build_cluster_artifacts(
        prepared_items,
        batch_result["batch_summaries"],
        embedding_provider,
        config.cluster_similarity_threshold,
    )
    model_artifacts = classification_artifacts + embedding_artifacts + cluster_artifacts
    model_artifacts_path = config.processed_dir / f"{run_id}_model_artifacts.json"
    embedding_artifacts_path = config.processed_dir / f"{run_id}_embedding_artifacts.json"
    cluster_artifacts_path = config.processed_dir / f"{run_id}_cluster_artifacts.json"
    write_json(model_artifacts_path, model_artifacts)
    write_json(embedding_artifacts_path, embedding_artifacts)
    write_json(cluster_artifacts_path, cluster_artifacts)

    analysis = analyze_venture_signals(prepared_items, config, run_id, filtering_summary, relevance_summary)
    write_json(config.processed_dir / f"{run_id}_analysis.json", analysis)

    csv_paths = export_csv_outputs(analysis, prepared_items, config.csv_dir, run_id, excluded_items, cluster_artifacts)
    markdown_path = export_markdown_report(analysis, config.markdown_dir, run_id, cluster_artifacts)
    html_path = export_html_report(analysis, config.html_dir, run_id, cluster_artifacts)
    save_run_to_sqlite(
        config.sqlite_path,
        run_id,
        analysis,
        collector_diagnostics,
        raw_items,
        prepared_items,
        excluded_items,
        relevance_excluded_items,
        batch_result["batch_summaries"],
    )
    save_model_artifacts(config.sqlite_path, run_id, model_artifacts)

    logger.info("Venture signal pipeline complete.")
    logger.info("Run ID: %s", run_id)
    logger.info("Live retrieval summary:")
    logger.info("  Source 1 endpoint used: %s", source1_diagnostics["endpoint"])
    logger.info("  Source 1 query used: %s", source1_diagnostics["query_used"])
    logger.info("  Source 1 live items fetched count: %s", source1_diagnostics["live_items_fetched_count"])
    logger.info("  Source 1 fallback triggered? %s", _yes_no(source1_diagnostics["fallback_triggered"]))
    logger.info("  Source 1 failure type: %s", source1_diagnostics["failure_type"] or "none")
    logger.info("  Source 1 failure reason: %s", source1_diagnostics["fallback_reason"] or "none")
    logger.info("  Resume from run ID: %s", config.resume_from_run_id or "none")
    logger.info("  Cross-run duplicate items skipped: %s", len(cross_run_duplicate_items))
    logger.info("  Processing batch size: %s", config.processing_batch_size)
    logger.info("  Embedding backend: %s", config.embedding_backend)
    logger.info("  Embedding model: %s", config.embedding_model or "default")
    logger.info("  Cluster similarity threshold: %s", config.cluster_similarity_threshold)
    logger.info("  Collection policy: %s", analysis["run_metadata"]["collection_policy"])
    logger.info("  Source 2 Stack Exchange endpoint used: %s", source2_diagnostics["endpoint"])
    logger.info("  Source 2 Stack Exchange site used: %s", source2_diagnostics["stackexchange_site"])
    logger.info("  Source 2 Stack Exchange query family used: %s", source2_diagnostics["stackexchange_query"])
    logger.info("  Source 2 Stack Exchange request params: %s", source2_diagnostics["request_params"])
    logger.info("  Source 2 live question count fetched: %s", source2_diagnostics["live_question_count_fetched"])
    logger.info("  Source 2 live usable question items fetched: %s", source2_diagnostics["live_items_fetched_count"])
    logger.info("  Source 2 fallback triggered? %s", _yes_no(source2_diagnostics["fallback_triggered"]))
    logger.info("  Source 2 failure type: %s", source2_diagnostics["failure_type"] or "none")
    logger.info("  Source 2 failure reason: %s", source2_diagnostics["fallback_reason"] or "none")
    logger.info("  Final fallback item count: %s", collector_diagnostics["final_fallback_item_count"])
    logger.info("Collector diagnostics JSON: %s", collector_diagnostics_path)
    logger.info("Filtering summary:")
    logger.info("  Raw items collected: %s", filtering_summary["raw_items_collected"])
    logger.info("  Filtered out: %s", filtering_summary["filtered_out_items"])
    logger.info("  Evidence candidates: %s", filtering_summary["evidence_candidate_items"])
    logger.info("  Raw by source: %s", filtering_summary["raw_by_source"])
    logger.info("  Kept by source: %s", filtering_summary["kept_by_source"])
    logger.info("  Excluded by source: %s", filtering_summary["excluded_by_source"])
    logger.info("  Top exclusion reasons: %s", filtering_summary["top_exclusion_reasons"])
    logger.info("Relevance summary:")
    logger.info("  After quality filter: %s", len(candidate_items))
    logger.info("  After relevance filter: %s", len(prepared_items))
    logger.info("  Relevance-filtered items: %s", len(relevance_excluded_items))
    logger.info("Relevance-excluded items JSON: %s", relevance_excluded_path)
    logger.info("Model artifacts JSON: %s", model_artifacts_path)
    logger.info("Model artifacts generated: %s", len(model_artifacts))
    logger.info("Embedding artifacts JSON: %s", embedding_artifacts_path)
    logger.info("Embedding artifacts generated: %s", len(embedding_artifacts))
    logger.info("Cluster artifacts JSON: %s", cluster_artifacts_path)
    logger.info("Cluster artifacts generated: %s", len(cluster_artifacts))
    if excluded_items:
        logger.info("  Sample exclusions:")
        for item in excluded_items[:3]:
            logger.info("    - %s %s: %s", item["source_type"], item["source_id"], item["exclude_reasons"])
    logger.info("Filtering summary JSON: %s", filtering_summary_path)
    logger.info("Excluded items JSON: %s", excluded_items_path)
    logger.info("Cross-run duplicate items JSON: %s", cross_run_duplicate_path)
    logger.info("Batch summary JSON: %s", batch_summary_path)
    logger.info("CSV evidence: %s", csv_paths["evidence_csv"])
    logger.info("CSV normalized items: %s", csv_paths["items_csv"])
    logger.info("CSV summary: %s", csv_paths["summary_csv"])
    logger.info("CSV excluded items: %s", csv_paths["excluded_csv"])
    logger.info("CSV evidence clusters: %s", csv_paths["clusters_csv"])
    logger.info("Markdown report: %s", markdown_path)
    logger.info("HTML report: %s", html_path)
    logger.info("SQLite run index: %s", config.sqlite_path)


def _configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")


def _yes_no(value: bool | None) -> str:
    if value is True:
        return "yes"
    if value is False:
        return "no"
    return "unknown"


def _load_raw_items(path: str) -> list[dict]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Raw items file must contain a JSON list.")
    return data


def _resume_start_pages(config: PipelineConfig) -> tuple[dict[str, int] | None, dict[str, int] | None]:
    if not config.resume_from_run_id:
        return None, None
    return (
        get_resume_start_pages(config.sqlite_path, config.resume_from_run_id, "source1_discussion"),
        get_resume_start_pages(config.sqlite_path, config.resume_from_run_id, "source2_stackoverflow_questions"),
    )


def _dedupe_resume_raw_items(config: PipelineConfig, raw_items: list[dict]) -> tuple[list[dict], list[dict]]:
    if not config.resume_from_run_id:
        return raw_items, []

    lineage_run_ids = get_resume_lineage_run_ids(config.sqlite_path, config.resume_from_run_id)
    prior_keys = get_raw_item_source_keys(config.sqlite_path, lineage_run_ids)
    kept_items = []
    duplicate_items = []
    for item in raw_items:
        key = (item.get("source_name", ""), item.get("source_id", ""))
        if key in prior_keys:
            duplicate = dict(item)
            duplicate["duplicate_reason"] = "seen_in_resume_chain"
            duplicate["resume_from_run_id"] = config.resume_from_run_id
            duplicate_items.append(duplicate)
        else:
            kept_items.append(item)
    return kept_items, duplicate_items


def _local_file_diagnostics(config: PipelineConfig, raw_items: list[dict]) -> tuple[dict, dict]:
    discussion_count = sum(1 for item in raw_items if item.get("source_type") == "discussion")
    review_count = sum(1 for item in raw_items if item.get("source_type") == "review")
    source_path = f"local_file:{config.raw_items_file}"
    return (
        CollectorDiagnostics(
            source="source1_discussion",
            endpoint=source_path,
            query_used=config.community_queries,
            expected_response_format="Local raw item JSON list.",
            live_items_fetched_count=discussion_count,
            fallback_triggered=False,
        ).to_dict(),
        CollectorDiagnostics(
            source="source2_stackoverflow_questions",
            endpoint=source_path,
            stackexchange_site=config.stackexchange_site,
            stackexchange_query=config.stackexchange_queries,
            expected_response_format="Local raw item JSON list.",
            live_question_count_fetched=review_count,
            live_items_fetched_count=review_count,
            fallback_triggered=False,
        ).to_dict(),
    )


def _disabled_source_diagnostics(config: PipelineConfig, source_key: str) -> dict:
    if source_key == "source1":
        return CollectorDiagnostics(
            source="source1_discussion",
            endpoint="disabled",
            query_used=config.community_queries,
            expected_response_format="Source disabled by run configuration.",
            fallback_triggered=False,
        ).to_dict()
    return CollectorDiagnostics(
        source="source2_stackoverflow_questions",
        endpoint="disabled",
        stackexchange_site=config.stackexchange_site,
        stackexchange_query=config.stackexchange_queries,
        expected_response_format="Source disabled by run configuration.",
        fallback_triggered=False,
    ).to_dict()


if __name__ == "__main__":
    main()
