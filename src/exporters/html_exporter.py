"""Static HTML report exporter."""

from html import escape
from pathlib import Path


def export_html_report(
    analysis: dict,
    output_dir: Path,
    run_id: str,
    cluster_artifacts: list[dict] | None = None,
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{run_id}_venture_signal_memo.html"
    path.write_text(_render_html(analysis, cluster_artifacts or []), encoding="utf-8")
    return path


def _render_html(analysis: dict, cluster_artifacts: list[dict]) -> str:
    meta = analysis["run_metadata"]
    volume = analysis["volume"]
    filtering = analysis.get("filtering_summary", {})
    relevance = analysis.get("relevance_summary", {})
    sections = []

    for summary in analysis["category_summaries"].values():
        examples = "".join(
            f"<li><strong>Score {escape(str(summary.get('example_scores', [''])[index]))}</strong>: {escape(example)}</li>"
            for index, example in enumerate(summary["example_evidence"])
        )
        if not examples:
            examples = "<li>No example evidence surfaced in this run.</li>"
        sections.append(
            f"""
            <section>
              <h2>{escape(summary['title'])}</h2>
              <p>{escape(summary['summary'])}</p>
              <ul>{examples}</ul>
            </section>
            """
        )

    uncertainty = "".join(f"<li>{escape(note)}</li>" for note in analysis["uncertainty_notes"])
    implications = "".join(f"<li>{escape(item)}</li>" for item in analysis["venture_implications"])
    limitations = "".join(f"<li>{escape(item)}</li>" for item in analysis["limitations"])
    sources = "".join(
        f"<li><strong>{escape(source['source_name'])}</strong>: {escape(source['role'])}</li>"
        for source in analysis["data_sources"]
    )
    exclusion_reasons = ", ".join(
        f"{escape(str(reason))}={escape(str(count))}"
        for reason, count in filtering.get("top_exclusion_reasons", {}).items()
    ) or "none"
    clusters = _render_clusters(cluster_artifacts)

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(meta['project_title'])}</title>
  <style>
    body {{
      margin: 0;
      font-family: Arial, Helvetica, sans-serif;
      color: #17202a;
      background: #f6f7f9;
      line-height: 1.55;
    }}
    header {{
      background: #102a43;
      color: #ffffff;
      padding: 36px 24px;
    }}
    main {{
      max-width: 980px;
      margin: 0 auto;
      padding: 24px;
      background: #ffffff;
    }}
    h1, h2 {{
      margin-top: 0;
    }}
    h1 {{
      font-size: 30px;
      line-height: 1.2;
    }}
    h2 {{
      border-bottom: 1px solid #d9e2ec;
      padding-bottom: 8px;
      margin-top: 30px;
      color: #102a43;
    }}
    .metadata {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 12px;
      margin-top: 18px;
    }}
    .metadata div {{
      background: #eef2f6;
      border-left: 4px solid #2f80ed;
      padding: 10px 12px;
    }}
    .volume {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 12px;
      padding: 0;
      list-style: none;
    }}
    .volume li {{
      background: #f3f6f9;
      padding: 12px;
      border: 1px solid #d9e2ec;
    }}
    .cluster-list {{
      display: grid;
      gap: 16px;
    }}
    .cluster {{
      border: 1px solid #d9e2ec;
      padding: 16px;
      background: #fbfcfd;
    }}
    .cluster h3 {{
      margin: 0 0 8px;
      color: #102a43;
    }}
    .cluster dl {{
      display: grid;
      grid-template-columns: 160px 1fr;
      gap: 8px 14px;
      margin: 12px 0;
    }}
    .cluster dt {{
      font-weight: bold;
      color: #52606d;
    }}
    .cluster dd {{
      margin: 0;
    }}
    footer {{
      color: #52606d;
      font-size: 14px;
      margin-top: 36px;
      padding-top: 18px;
      border-top: 1px solid #d9e2ec;
    }}
  </style>
</head>
<body>
  <header>
    <h1>{escape(meta['project_title'])}</h1>
    <p>Supplementary weak-signal evidence memo for uncertainty-aware early-stage venture evaluation.</p>
  </header>
  <main>
    <section>
      <h2>Project Title and Run Metadata</h2>
      <div class="metadata">
        <div><strong>Run ID</strong><br>{escape(meta['run_id'])}</div>
        <div><strong>Generated UTC</strong><br>{escape(meta['generated_at_utc'])}</div>
        <div><strong>Venture Category</strong><br>{escape(meta['venture_category'])}</div>
        <div><strong>Community Query Family</strong><br>{escape('; '.join(meta['community_queries']))}</div>
        <div><strong>Stack Exchange Site</strong><br>{escape(meta['stackexchange_site'])}</div>
        <div><strong>Stack Exchange Query Family</strong><br>{escape('; '.join(meta['stackexchange_queries']))}</div>
        <div><strong>Max Discussion Items</strong><br>{escape(str(meta.get('max_discussion_items', 'n/a')))}</div>
        <div><strong>Max Review Items</strong><br>{escape(str(meta.get('max_review_items', 'n/a')))}</div>
        <div><strong>Request Timeout</strong><br>{escape(str(meta.get('request_timeout', 'n/a')))} seconds</div>
        <div><strong>Debug Raw Saved</strong><br>{escape(str(meta.get('debug_save_raw', 'n/a')))}</div>
        <div><strong>Raw Items File</strong><br>{escape(str(meta.get('raw_items_file') or 'none'))}</div>
      </div>
    </section>

    <section>
      <h2>Data Sources Used</h2>
      <ul>{sources}</ul>
    </section>

    <section>
      <h2>Volume of Evidence Analyzed</h2>
      <ul class="volume">
        <li><strong>{volume['total_items_analyzed']}</strong><br>Total items</li>
        <li><strong>{volume['discussion_items']}</strong><br>Discussion items</li>
        <li><strong>{volume['review_items']}</strong><br>Review items</li>
        <li><strong>{volume['evidence_rows']}</strong><br>Evidence rows</li>
        <li><strong>{volume['demo_fallback_items']}</strong><br>Fallback items</li>
      </ul>
      <h3>Text-Quality Filtering</h3>
      <ul>
        <li>Raw items collected: {filtering.get('raw_items_collected', 'n/a')}</li>
        <li>Filtered out: {filtering.get('filtered_out_items', 'n/a')}</li>
        <li>Evidence candidates retained: {filtering.get('evidence_candidate_items', 'n/a')}</li>
        <li>Top exclusion reasons: {exclusion_reasons}</li>
      </ul>
      <h3>Evidence Relevance Ranking</h3>
      <ul>
        <li>Candidates after quality filter: {relevance.get('evidence_candidates_after_quality_filter', 'n/a')}</li>
        <li>Candidates after relevance filter: {relevance.get('evidence_candidates_after_relevance_filter', 'n/a')}</li>
        <li>Relevance-filtered items: {relevance.get('relevance_filtered_items', 'n/a')}</li>
      </ul>
    </section>

    <section>
      <h2>Pain Point Clusters</h2>
      {clusters}
    </section>

    {''.join(sections)}

    <section>
      <h2>Key Uncertainty Notes</h2>
      <ul>{uncertainty}</ul>
    </section>

    <section>
      <h2>Implications for Early-Stage Venture Evaluation</h2>
      <ul>{implications}</ul>
    </section>

    <section>
      <h2>Limitations / Why This Does Not Replace Human Judgement</h2>
      <ul>{limitations}</ul>
    </section>

    <footer>
      This report is decision-support evidence only. It is not financial advice or an automated investment recommendation.
    </footer>
  </main>
</body>
</html>
"""


def _render_clusters(cluster_artifacts: list[dict]) -> str:
    if not cluster_artifacts:
        return "<p>No evidence clusters generated for this run.</p>"

    clusters = []
    for artifact in cluster_artifacts:
        cluster = artifact["artifact"]
        excerpts = "".join(
            f"<li>{escape(excerpt)}</li>"
            for excerpt in cluster.get("evidence_excerpts", [])[:3]
        )
        if not excerpts:
            excerpts = "<li>No representative evidence excerpt stored.</li>"
        clusters.append(
            f"""
            <article class="cluster">
              <h3>{escape(cluster['label'])}</h3>
              <dl>
                <dt>Cluster ID</dt><dd>{escape(cluster['cluster_id'])}</dd>
                <dt>Items</dt><dd>{escape(str(cluster['item_count']))}</dd>
                <dt>Source mix</dt><dd>{escape(_format_dict(cluster.get('source_mix', {})))}</dd>
                <dt>Avg relevance</dt><dd>{escape(str(cluster.get('average_relevance_score', 'n/a')))}</dd>
                <dt>Opportunity</dt><dd>{escape(cluster['product_opportunity'])}</dd>
                <dt>Top terms</dt><dd>{escape(_format_list(cluster.get('top_terms', [])) or 'none')}</dd>
                <dt>Representatives</dt><dd>{escape(_format_list(cluster.get('representative_item_ids', [])) or 'none')}</dd>
                <dt>Grouping basis</dt><dd>{escape(cluster.get('grouping_basis', 'n/a'))}</dd>
              </dl>
              <ul>{excerpts}</ul>
            </article>
            """
        )
    return f"<div class=\"cluster-list\">{''.join(clusters)}</div>"


def _format_dict(value: dict) -> str:
    if not value:
        return "none"
    return ", ".join(f"{key}={count}" for key, count in value.items())


def _format_list(value: list[str]) -> str:
    return "; ".join(value)
