# Development Plan

This document records the next development direction for the AI-Assisted Community Signal Pipeline. It should be read together with `AGENT.md`, `PROJECT_STATE.md`, `README.md`, and `docs/product_brief.md`.

## Current Baseline

The current baseline is an end-to-end public-signal pipeline:

1. Collect public text through documented APIs.
2. Normalize and clean source records while preserving provenance.
3. Filter low-quality evidence such as jobs, promotional copy, directory snippets, and weakly relevant discussion.
4. Score relevance with transparent heuristic dictionaries.
5. Extract weak-signal categories using keyword and pattern rules.
6. Export JSON, CSV, Markdown, and static HTML reports.

The current system is not a trained NLP model, not an ML predictor, and not an investment recommendation engine.

## Development Thesis

The project should evolve from a runnable pipeline demo into a traceable evidence-review product for early-stage venture-category diligence.

The strongest next version would combine:

- A more reliable backend pipeline.
- Clear user-controlled query configuration.
- Better semantic NLP support.
- Optional LLM-assisted summarization with evidence links.
- A dashboard for filtering, inspecting, and comparing evidence.
- A lightweight evaluation workflow for precision, ranking quality, and usefulness.

The project should continue to emphasize uncertainty, provenance, and human judgement.

## Near-Term Backend Priorities

### 1. Testing and Regression Safety

Status: initial baseline tests added in `tests/test_baseline_pipeline.py`; deterministic raw sample added at `samples/small_business_operations_raw_items.json`.

Continue expanding the `tests/` suite before major feature work.

Initial test targets:

- `clean_text` and `excerpt`.
- Quality-filter inclusion and exclusion cases.
- Relevance scoring for strong, weak, promotional, and off-topic examples.
- Signal extraction category behavior.
- CSV, Markdown, and HTML exporters on empty and non-empty analysis results.
- Collector mapping functions using fixture API responses.

The tests should include deterministic sample records so future changes do not silently weaken filtering or ranking quality.

Current coverage includes:

- Text cleaning and excerpt behavior.
- Quality-filter keep/exclude behavior.
- Relevance preparation for relevant and off-topic items.
- Analyzer output guardrails.
- CSV, Markdown, and HTML exporter smoke tests.
- Collector mapping functions using fixture API records.
- Local raw-items file loading and source-count diagnostics.

### 2. Typed Data Contracts

Status: dataclass contracts added in `src/models.py` for raw items, prepared items, evidence rows, collector diagnostics, filtering summaries, relevance summaries, run metadata, volume summaries, and analysis results.

Continue replacing loose cross-module dictionaries with explicit schemas or dataclasses where it simplifies the pipeline.

Candidate schemas:

- `RawItem`: implemented.
- `PreparedItem`: implemented.
- `EvidenceRow`: implemented.
- `CollectorDiagnostics`: implemented.
- `FilteringSummary`: implemented.
- `RelevanceSummary`: implemented.
- `RunMetadata`: implemented.
- `VolumeSummary`: implemented.
- `AnalysisResult`: implemented.
- `RunConfig`

This should make the pipeline easier to extend into a CLI, API service, database-backed workflow, or dashboard.

### 3. CLI and Config Files

Status: CLI argument support, JSON config-file support, and per-source collection-policy controls are implemented.

Users can now run:

```bash
python src/main.py \
  --theme "AI tools for real estate agents" \
  --community-queries "real estate CRM pain;agent workflow automation" \
  --stackexchange-queries "crm webhook issue;real estate api integration" \
  --max-discussion-items 50 \
  --max-review-items 50 \
  --discussion-page-size 25 \
  --discussion-max-pages-per-query 2 \
  --review-page-size 25 \
  --review-max-pages-per-query 2
```

JSON config files can also be used:

```bash
python src/main.py --config configs/example_run.json
```

CLI arguments take priority over JSON config files, which take priority over environment variables, which take priority over built-in defaults.

Local raw-item files can be used for offline demos:

```bash
python src/main.py --raw-items-file samples/small_business_operations_raw_items.json
```

Every output run should preserve the exact theme, query families, limits, source settings, timestamp, and code version where practical.

Current collection-policy controls include source enable/disable flags, per-source item limits, per-source page size, per-query page depth, Hacker News sort order, Stack Exchange sort/order, request timeout, and downstream processing batch size.

### 4. Collector Robustness

Status: Hacker News now has retry behavior aligned with the Stack Exchange collector. Both collectors now expose page iterators for bounded paginated collection, and page size, page depth, and sort settings are configurable from the run config.

Hacker News and Stack Exchange collectors should continue to share reliability patterns:

- Consistent retry behavior.
- Page-level collection interfaces.
- Narrow exception handling.
- Clear HTTP, timeout, parsing, and no-result diagnostics.
- Optional per-source enable/disable flags.
- Better rate-limit messages.
- Fixture-based tests for mapping and failure behavior.

Fallback demo records should remain available, but real programming errors should not be silently hidden as endpoint failure.

### 5. Runtime Logging

Status: runtime `print` calls in `main.py` and collectors have been replaced with standard `logging`. Verification passed with 23 unit tests and offline sample run `20260525_204847`.

Future logging work should stay minimal:

- Keep terminal output readable.
- Include run context where it improves operations.
- Avoid noisy debug logs unless a source or pipeline stage needs inspection.
- Do not add a logging framework beyond the standard library unless the runtime architecture requires it.

## NLP and ML Development Direction

### 1. Semantic Deduplication and Clustering

The first NLP upgrade is an embedding-assisted pain-point clustering baseline rather than prediction. It writes `embedding` artifacts through a configurable embedding provider and `evidence_cluster` artifacts through `heuristic-evidence-clusterer@v2`. The default provider remains `hashed-text-embedding@v1`; an optional local `sentence-transformer-embedding@v1` backend can be enabled for stronger semantic similarity.

Useful goals:

- Group repeated evidence about the same pain. Initial deterministic grouping is implemented.
- Reduce duplicate Stack Overflow implementation issues.
- Surface cluster-level summaries.
- Show representative evidence for each cluster.

Possible approaches:

- Current lightweight hashing embeddings. Implemented.
- Optional local sentence-transformer embedding backend. Initial adapter implemented.
- Cluster evaluation with reviewed source-level labels. Initial harness implemented.
- Cluster review export for human labeling. Initial exporter implemented.
- Threshold sweep evaluation with JSON and CSV outputs for cluster tuning. Implemented.
- Backend comparison across embedding providers and thresholds. Implemented.
- Embeddings plus cosine similarity.
- Local sentence-transformer model.
- Lightweight clustering such as agglomerative clustering or HDBSCAN.

### 2. Better Classification

After a deterministic sample set exists, add supervised or weakly supervised classifiers for:

- Evidence quality.
- Venture-category relevance.
- Signal category labels.
- Adoption barrier type.
- Business context strength.

This should be evaluated against human-reviewed examples before replacing heuristic logic.

### 3. LLM-Assisted Summarization

LLM support should be optional and evidence-grounded.

Safe use cases:

- Summarize clusters with citations.
- Draft uncertainty notes.
- Generate diligence questions from evidence rows.
- Rewrite report sections for readability.

Boundaries:

- Always retain source-linked evidence.
- Do not let the LLM invent facts, companies, metrics, or investment conclusions.
- Keep deterministic baseline outputs available for comparison.

### 4. No Investment Prediction Layer

Do not build:

- Return prediction.
- Invest/do-not-invest classifier.
- Automated investment score.
- Founder or company social scoring.
- Portfolio allocation advice.

If a scoring layer is added, it should score evidence quality, relevance, uncertainty, or review priority.

## Frontend and Dashboard Direction

The current HTML report is a static artifact. The next product step is an interactive evidence-review dashboard.

Useful dashboard features:

- Enter venture category and custom query families.
- Run or reload a pipeline analysis.
- Filter evidence by source, query, category, score, fallback status, and date.
- Inspect raw text, cleaned text, source URL, quality reasons, relevance reasons, and penalties.
- Compare runs side by side.
- View section summaries and evidence distributions.
- Export selected evidence to CSV, Markdown, or memo format.
- Mark evidence as useful, noisy, duplicate, or misclassified.

Suggested implementation paths:

- Streamlit for a fast research demo.
- FastAPI plus React for a more product-like architecture.

Start with Streamlit if the goal is portfolio speed. Move to FastAPI plus React if the goal is production architecture.

## Data and Storage Direction

The MVP writes JSON and CSV files. That is enough for the baseline, but a dashboard or multi-run workflow will benefit from a database.

Possible next steps:

- Keep file outputs as export artifacts.
- Add SQLite for local runs. Initial SQLite run indexing is implemented at `data/storage/pipeline_runs.sqlite3`.
- Use `list_runs`, `get_run_summary`, `get_collection_pages`, `get_collection_states`, `get_processing_batches`, `get_model_artifacts`, `get_embedding_artifacts`, `get_cluster_artifacts`, `get_run_chain_summary`, `get_run_chain_evidence_rows`, `get_run_chain_model_artifacts`, `get_run_chain_embedding_artifacts`, `get_run_chain_cluster_artifacts`, and `get_evidence_rows` as the read layer for run comparison and dashboard browsing.
- Use `src/inspect_runs.py` as the first read-only CLI over the local run index.
- Store run metadata, raw items, normalized items, evidence rows, filtering logs, and diagnostics in separate tables.
- Keep source URLs and original source IDs as first-class fields.

Avoid collapsing raw, processed, and interpreted data into one table.

## Large-Scale Collection and Analysis Direction

See `docs/scale_strategy.md` for the full scale plan.

The project should not scale by turning the current single-run script into an unbounded in-memory crawler. Large-scale support should be built around:

- Paginated public API source adapters.
- Explicit source and query limits.
- Incremental collection with resumable run state.
- Durable storage before downstream processing.
- Batch filtering, relevance scoring, signal extraction, and clustering.
- Deduplication across runs using source name plus source ID.
- Dashboard queries over stored summaries and paginated evidence tables.

Near-term scale work started with SQLite and a run index. Paginated collector interfaces, page-level persistence, explicit per-source/query collection state, a read-only inspection CLI, live resume from stored next-page state, source-key deduplication across resume chains, batch filtering/relevance preparation, SQLite batch status persistence, a generic model artifact layer, deterministic classification artifacts, lightweight embedding artifacts, an optional local transformer embedding adapter, embedding-assisted evidence-cluster artifacts, a cluster review export, a cluster evaluation harness with threshold sweep and backend comparison support, aggregate views across resumed run chains, and configurable collection policies are now implemented. The next scale step is tuning transformer-backed clustering before adding heavier external NLP/ML models, async jobs, distributed execution, or larger analytical stores.

## Evaluation Direction

The project needs a small human evaluation layer before serious NLP or ML claims.

Suggested rubric:

- Is the item user-generated or user-facing?
- Is it relevant to the venture category?
- Does it show concrete operational pain, unmet need, adoption barrier, dissatisfaction, demand clue, or competitor mention?
- Is the source link sufficient for review?
- Is the extracted category correct?
- Is the report section useful for a human evaluator?

Track:

- Filtering precision.
- Relevance-ranking quality.
- Category-label accuracy.
- Duplicate rate.
- Human usefulness rating.

## Suggested Milestones

### Milestone 1: Engineering Hardening

- Add tests.
- Add schemas.
- Add CLI args.
- Improve collector retry and error handling.
- Add deterministic sample dataset.

### Milestone 2: User-Controlled Runs

- Add config-file support.
- Save complete run metadata.
- Improve Markdown and HTML reports.
- Add run comparison support at the data level.
- Add local storage and run indexing as the first step toward larger-scale analysis. Initial implementation completed.
- Add a CLI inspection command over stored runs and collection state. Completed.
- Add live resume behavior using stored collection state. Completed.
- Add source-key deduplication across resumed run chains. Completed.
- Add batch filtering and relevance preparation while preserving output shape. Completed.
- Add SQLite processing batch persistence. Completed.
- Add a generic model artifact layer. Completed.
- Add deterministic classification artifact producer. Completed.
- Add aggregate views across resumed run chains. Completed.
- Add configurable collection-policy controls for page size, page depth, sort order, and source enablement. Completed.
- Add lightweight embedding artifacts and inspection CLI support. Completed.
- Add evidence-cluster artifacts and inspection CLI support. Completed.
- Upgrade cluster assignment to use pain-mechanism buckets plus embedding similarity. Completed.
- Add cluster-first Markdown, HTML, and CSV report exports. Completed.
- Add optional local sentence-transformer embedding backend. Initial adapter completed.
- Add cluster evaluation against reviewed labels. Initial harness completed.
- Add cluster review export for human labeling. Initial exporter completed.
- Add threshold sweep support for cluster evaluation. Completed.
- Add backend comparison support for cluster evaluation. Completed.

### Milestone 3: Research-Grade Evidence Layer

- Expand reviewed cluster labels and tune transformer-backed embedding artifacts for semantic deduplication.
- Add clustering beyond deterministic pain-mechanism groups.
- Add human evaluation labels.
- Tune relevance and category extraction against labeled examples.

### Milestone 4: Dashboard MVP

- Build evidence table UI.
- Add filters and source inspection.
- Add custom query form.
- Add run summary visualizations.
- Add manual feedback labels.

### Milestone 5: Optional AI Assistance

- Add evidence-grounded LLM summarization.
- Add diligence-question generation.
- Add uncertainty-aware cluster summaries.
- Keep deterministic baseline outputs for auditability.

## Open Questions

- Should the first UI be Streamlit for speed or FastAPI plus React for architecture?
- Should custom user queries be stored only in run metadata or also in reusable named configs?
- Which embedding model is acceptable for local, reproducible clustering?
- How much live public data should be saved by default for portfolio demos?
- What is the smallest useful labeled dataset for evaluating quality filtering and relevance ranking?
