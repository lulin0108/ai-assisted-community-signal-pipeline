"""Run the end-to-end venture signal pipeline."""

from analyzers.venture_signal_analyzer import analyze_venture_signals
from collectors.source1_collector import collect_discussion_items
from collectors.source2_collector import collect_review_items
from config import PipelineConfig
from exporters.csv_exporter import export_csv_outputs
from exporters.html_exporter import export_html_report
from exporters.markdown_exporter import export_markdown_report
from processors.text_quality_filter import filter_quality_items
from processors.prepare_items import prepare_items
from utils.file_utils import ensure_directories, make_run_id, write_json


def main() -> None:
    config = PipelineConfig.from_env()
    ensure_directories(
        [
            config.raw_dir,
            config.processed_dir,
            config.csv_dir,
            config.markdown_dir,
            config.html_dir,
        ]
    )

    run_id = make_run_id()

    discussion_items, source1_diagnostics = collect_discussion_items(config)
    review_items, source2_diagnostics = collect_review_items(config)
    raw_items = discussion_items + review_items
    write_json(config.raw_dir / f"{run_id}_raw_items.json", raw_items)

    collector_diagnostics = {
        "source1": source1_diagnostics,
        "source2": source2_diagnostics,
        "final_fallback_item_count": sum(1 for item in raw_items if item.get("is_demo_fallback")),
        "debug_save_raw": config.debug_save_raw,
    }
    collector_diagnostics_path = config.raw_dir / f"{run_id}_collector_diagnostics.json"
    write_json(collector_diagnostics_path, collector_diagnostics)

    candidate_items, excluded_items, filtering_summary = filter_quality_items(raw_items)
    filtering_summary_path = config.processed_dir / f"{run_id}_filtering_summary.json"
    excluded_items_path = config.processed_dir / f"{run_id}_excluded_items.json"
    write_json(filtering_summary_path, filtering_summary)
    write_json(excluded_items_path, excluded_items)

    prepared_items, relevance_excluded_items = prepare_items(candidate_items)
    relevance_excluded_path = config.processed_dir / f"{run_id}_relevance_excluded_items.json"
    write_json(config.processed_dir / f"{run_id}_normalized_items.json", prepared_items)
    write_json(relevance_excluded_path, relevance_excluded_items)

    analysis = analyze_venture_signals(prepared_items, config, run_id)
    analysis["filtering_summary"] = filtering_summary
    analysis["relevance_summary"] = {
        "evidence_candidates_after_quality_filter": len(candidate_items),
        "evidence_candidates_after_relevance_filter": len(prepared_items),
        "relevance_filtered_items": len(relevance_excluded_items),
    }
    write_json(config.processed_dir / f"{run_id}_analysis.json", analysis)

    csv_paths = export_csv_outputs(analysis, prepared_items, config.csv_dir, run_id, excluded_items)
    markdown_path = export_markdown_report(analysis, config.markdown_dir, run_id)
    html_path = export_html_report(analysis, config.html_dir, run_id)

    print("Venture signal pipeline complete.")
    print(f"Run ID: {run_id}")
    print("Live retrieval summary:")
    print(f"  Source 1 endpoint used: {source1_diagnostics['endpoint']}")
    print(f"  Source 1 query used: {source1_diagnostics['query_used']}")
    print(f"  Source 1 live items fetched count: {source1_diagnostics['live_items_fetched_count']}")
    print(f"  Source 1 fallback triggered? {_yes_no(source1_diagnostics['fallback_triggered'])}")
    print(f"  Source 1 failure type: {source1_diagnostics['failure_type'] or 'none'}")
    print(f"  Source 1 failure reason: {source1_diagnostics['fallback_reason'] or 'none'}")
    print(f"  Source 2 Stack Exchange endpoint used: {source2_diagnostics['endpoint']}")
    print(f"  Source 2 Stack Exchange site used: {source2_diagnostics['stackexchange_site']}")
    print(f"  Source 2 Stack Exchange query family used: {source2_diagnostics['stackexchange_query']}")
    print(f"  Source 2 Stack Exchange request params: {source2_diagnostics['request_params']}")
    print(f"  Source 2 live question count fetched: {source2_diagnostics['live_question_count_fetched']}")
    print(f"  Source 2 live usable question items fetched: {source2_diagnostics['live_items_fetched_count']}")
    print(f"  Source 2 fallback triggered? {_yes_no(source2_diagnostics['fallback_triggered'])}")
    print(f"  Source 2 failure type: {source2_diagnostics['failure_type'] or 'none'}")
    print(f"  Source 2 failure reason: {source2_diagnostics['fallback_reason'] or 'none'}")
    print(f"  Final fallback item count: {collector_diagnostics['final_fallback_item_count']}")
    print(f"Collector diagnostics JSON: {collector_diagnostics_path}")
    print("Filtering summary:")
    print(f"  Raw items collected: {filtering_summary['raw_items_collected']}")
    print(f"  Filtered out: {filtering_summary['filtered_out_items']}")
    print(f"  Evidence candidates: {filtering_summary['evidence_candidate_items']}")
    print(f"  Raw by source: {filtering_summary['raw_by_source']}")
    print(f"  Kept by source: {filtering_summary['kept_by_source']}")
    print(f"  Excluded by source: {filtering_summary['excluded_by_source']}")
    print(f"  Top exclusion reasons: {filtering_summary['top_exclusion_reasons']}")
    print("Relevance summary:")
    print(f"  After quality filter: {len(candidate_items)}")
    print(f"  After relevance filter: {len(prepared_items)}")
    print(f"  Relevance-filtered items: {len(relevance_excluded_items)}")
    print(f"Relevance-excluded items JSON: {relevance_excluded_path}")
    if excluded_items:
        print("  Sample exclusions:")
        for item in excluded_items[:3]:
            print(f"    - {item['source_type']} {item['source_id']}: {item['exclude_reasons']}")
    print(f"Filtering summary JSON: {filtering_summary_path}")
    print(f"Excluded items JSON: {excluded_items_path}")
    print(f"CSV evidence: {csv_paths['evidence_csv']}")
    print(f"CSV normalized items: {csv_paths['items_csv']}")
    print(f"CSV summary: {csv_paths['summary_csv']}")
    print(f"CSV excluded items: {csv_paths['excluded_csv']}")
    print(f"Markdown report: {markdown_path}")
    print(f"HTML report: {html_path}")


def _yes_no(value: bool | None) -> str:
    if value is True:
        return "yes"
    if value is False:
        return "no"
    return "unknown"


if __name__ == "__main__":
    main()
