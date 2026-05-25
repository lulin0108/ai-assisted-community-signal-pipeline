"""Markdown report exporter."""

from pathlib import Path


def export_markdown_report(analysis: dict, output_dir: Path, run_id: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{run_id}_venture_signal_memo.md"
    path.write_text(_render_markdown(analysis), encoding="utf-8")
    return path


def _render_markdown(analysis: dict) -> str:
    meta = analysis["run_metadata"]
    volume = analysis["volume"]
    filtering = analysis.get("filtering_summary", {})
    relevance = analysis.get("relevance_summary", {})
    lines = [
        f"# {meta['project_title']}",
        "",
        "## 1. Project Title and Run Metadata",
        "",
        f"- Run ID: `{meta['run_id']}`",
        f"- Generated at UTC: `{meta['generated_at_utc']}`",
        f"- Venture category: {meta['venture_category']}",
        f"- Community query family: {_format_list(meta['community_queries'])}",
        f"- Stack Exchange site: {meta['stackexchange_site']}",
        f"- Stack Exchange query family: {_format_list(meta['stackexchange_queries'])}",
        "",
        "## 2. Data Sources Used",
        "",
    ]

    for source in analysis["data_sources"]:
        lines.append(f"- {source['source_name']} ({source['source_type']}): {source['role']}")

    lines.extend(
        [
            "",
            "## 3. Scope / Venture Category / Query Family Analyzed",
            "",
            f"This run analyzes weak public signals for the venture category: **{meta['venture_category']}**.",
            "",
            "The memo is intended to support category-level venture evaluation under uncertainty, not review one specific app.",
            "",
            "## 4. Volume of Evidence Analyzed",
            "",
            f"- Total items analyzed: {volume['total_items_analyzed']}",
            f"- Discussion items: {volume['discussion_items']}",
            f"- Review items: {volume['review_items']}",
            f"- Extracted evidence rows: {volume['evidence_rows']}",
            f"- Demo fallback items: {volume['demo_fallback_items']}",
            "",
            "### Text-Quality Filtering",
            "",
            f"- Raw items collected: {filtering.get('raw_items_collected', 'n/a')}",
            f"- Filtered out: {filtering.get('filtered_out_items', 'n/a')}",
            f"- Evidence candidates retained: {filtering.get('evidence_candidate_items', 'n/a')}",
            f"- Top exclusion reasons: {_format_dict(filtering.get('top_exclusion_reasons', {}))}",
            "",
            "### Evidence Relevance Ranking",
            "",
            f"- Candidates after quality filter: {relevance.get('evidence_candidates_after_quality_filter', 'n/a')}",
            f"- Candidates after relevance filter: {relevance.get('evidence_candidates_after_relevance_filter', 'n/a')}",
            f"- Relevance-filtered items: {relevance.get('relevance_filtered_items', 'n/a')}",
            "",
        ]
    )

    section_numbers = {
        "recurring_problem_signals": "5",
        "unmet_needs": "6",
        "adoption_barriers": "7",
        "dissatisfaction_current_solutions": "8",
        "differentiation_opportunities": "9",
        "community_traction_clues": "10",
        "competing_solution_mentions": "11",
    }

    for category, summary in analysis["category_summaries"].items():
        lines.extend(
            [
                f"## {section_numbers[category]}. {summary['title']}",
                "",
                summary["summary"],
                "",
            ]
        )
        for index, example in enumerate(summary["example_evidence"]):
            score = summary.get("example_scores", [""])[index]
            lines.append(f"- Evidence (score {score}): {example}")
        if summary["example_evidence"]:
            lines.append("")

    lines.extend(["## 12. Key Uncertainty Notes", ""])
    lines.extend([f"- {note}" for note in analysis["uncertainty_notes"]])

    lines.extend(["", "## 13. Implications for Early-Stage Venture Evaluation", ""])
    lines.extend([f"- {item}" for item in analysis["venture_implications"]])

    lines.extend(["", "## 14. Limitations / Why This Does Not Replace Human Judgement", ""])
    lines.extend([f"- {item}" for item in analysis["limitations"]])
    lines.append("")
    return "\n".join(lines)


def _format_dict(value: dict) -> str:
    if not value:
        return "none"
    return ", ".join(f"{key}={count}" for key, count in value.items())


def _format_list(value: list[str]) -> str:
    return "; ".join(value)
