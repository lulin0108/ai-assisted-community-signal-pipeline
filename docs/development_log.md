# Development Log

This log records completed development steps, why they were made, and how they were verified.

## 2026-05-25

### Project Boundaries and Roadmap

- Updated `AGENT.md` with development boundaries, coding style expectations, and non-goals.
- Added `docs/development_plan.md` for the implementation roadmap.
- Reason: keep future work aligned with evidence-based decision support, not investment prediction.
- Verification: documentation review.
- Next: keep `PROJECT_STATE.md` and this log current after substantive work.

### Baseline Test Suite

- Added `tests/test_baseline_pipeline.py`.
- Covered text cleaning, quality filtering, relevance filtering, analyzer guardrails, exporters, collector mapping, config precedence, local sample input, and collector failure behavior.
- Reason: protect baseline behavior before larger refactors.
- Verification: `python -m unittest discover -s tests -v`.
- Next: add edge-case tests for empty outputs and filtering boundaries.

### CLI and Config Inputs

- Added CLI arguments through `PipelineConfig.from_args()`.
- Added JSON config-file support with `--config`.
- Added `configs/example_run.json`.
- Reason: let users run custom venture categories and query families without editing code or relying on environment variables.
- Verification: config precedence tests and live smoke runs.
- Next: add named presets only if repeated run patterns emerge.

### Data Contracts

- Added `src/models.py` with `PreparedItem` and `EvidenceRow`.
- Used those contracts in `prepare_items` and `analyze_venture_signals` while preserving dict-shaped outputs.
- Reason: reduce field drift across pipeline stages without adding heavy validation.
- Verification: model contract tests and live smoke run.
- Next: extend contracts only where they simplify raw items, diagnostics, summaries, or run config.

### Source Reliability

- Added retry behavior to the Hacker News collector.
- Narrowed collector fallback handling so source-boundary failures fallback, while programming errors propagate.
- Reason: improve reliability without hiding real code bugs.
- Verification: collector failure tests and offline smoke run.
- Next: keep collector diagnostics clear and avoid broad exception handling.

### Deterministic Offline Runs

- Added `--raw-items-file`.
- Added `samples/small_business_operations_raw_items.json`.
- Reason: support offline demos, screenshots, and regression checks without live API dependence.
- Verification: offline sample run `20260525_204202` and later smoke runs.
- Next: expand the sample set only when a specific demo or test need appears.

### Runtime Logging

- Replaced runtime `print` calls in `main.py` and collectors with standard `logging`.
- Reason: make terminal output easier to control and prepare for dashboard/API execution.
- Verification: `python -m unittest discover -s tests -v` passed with 23 tests; offline sample run `20260525_204847` completed with 5 raw items, 4 retained evidence candidates, and 0 fallback items.
- Next: add run-id-aware logging only when moving toward a service or dashboard runtime.

### Raw Item and Collector Diagnostics Contracts

- Added `RawItem` and `CollectorDiagnostics` contracts in `src/models.py`.
- Updated Hacker News, Stack Exchange, and local-file diagnostics paths to emit dicts from these contracts.
- Reason: reduce field drift at ingestion and diagnostics boundaries before adding dashboard, storage, or run comparison features.
- Verification: `python -m unittest discover -s tests -v` passed with 25 tests; offline sample run `20260525_205243` completed with 5 raw items, 4 retained evidence candidates, and 0 fallback items.
- Next: add contracts for filtering summaries or analysis results where they simplify exporter and dashboard work.

### Filtering Summary Contract

- Added `FilteringSummary` in `src/models.py`.
- Updated `text_quality_filter` to emit filtering summary dicts through the contract.
- Reason: stabilize report and future dashboard statistics for raw counts, retained counts, source counts, and exclusion reasons.
- Verification: `python -m unittest discover -s tests -v` passed with 26 tests; offline sample run `20260525_205422` completed with 5 raw items, 4 retained evidence candidates, and 0 fallback items.
- Next: add an analysis-result contract or run-metadata contract before building run comparison or dashboard features.

### Analysis and Run Metadata Contracts

- Added `RunMetadata`, `VolumeSummary`, `RelevanceSummary`, and `AnalysisResult` in `src/models.py`.
- Updated the analyzer to return a complete analysis result through the contract instead of having `main.py` mutate the analysis dict after creation.
- Reason: stabilize the shared report/dashboard shape for run metadata, volume statistics, filtering summary, relevance summary, evidence rows, and narrative sections.
- Verification: `python -m unittest discover -s tests -v` passed with 28 tests; offline sample run `20260525_205658` completed with 5 raw items, 4 retained evidence candidates, and 0 fallback items.
- Next: add empty-output exporter tests or start the first dashboard/run-comparison layer.

### Empty Output Tests and Scale Strategy

- Added tests for empty raw input and empty analysis exports.
- Added `docs/scale_strategy.md`.
- Updated `AGENT.md` and `docs/development_plan.md` with large-scale collection and analysis boundaries.
- Reason: ensure empty reports remain stable and establish that large-scale support should use pagination, durable storage, deduplication, and batch processing rather than an unbounded in-memory script.
- Verification: `python -m unittest discover -s tests -v` passed with 30 tests; offline sample run `20260525_210128` completed with 5 raw items, 4 retained evidence candidates, and 0 fallback items.
- Next: add local SQLite storage and a run index before dashboard-scale browsing or semantic clustering.

### SQLite Run Index

- Added `src/storage/sqlite_store.py`.
- Added local SQLite persistence at `data/storage/pipeline_runs.sqlite3`.
- Stored run metadata, collector diagnostics, raw items, prepared items, excluded items, relevance-excluded items, evidence rows, and category summaries in separate tables.
- Added `source_id` to evidence rows for stronger provenance and storage queries.
- Reason: create a durable local run index before run comparison, dashboard browsing, paginated collection, or semantic clustering.
- Verification: `python -m unittest discover -s tests -v` passed with 31 tests; offline sample run `20260525_210530` wrote to SQLite with 5 raw items and 20 evidence rows.
- Next: add a small run-list/query helper or begin paginated collector interfaces.

### SQLite Query Helpers

- Added `list_runs`, `get_run_summary`, and `get_evidence_rows` to `src/storage/sqlite_store.py`.
- Added tests for listing stored runs, loading run summaries, and reading paginated evidence rows with optional category filtering.
- Reason: make the SQLite run index usable by a dashboard, CLI, or run-comparison workflow without exposing table internals.
- Verification: `python -m unittest discover -s tests -v` passed with 32 tests; offline sample run `20260525_210730` wrote to SQLite; query helper smoke check returned the latest runs and top evidence rows.
- Next: add paginated collector interfaces before raising live collection limits substantially, or build a small dashboard over the SQLite query layer.

### Paginated Collector Interfaces

- Added `CollectedPage` in `src/models.py`.
- Added `iter_discussion_pages` for Hacker News and `iter_review_pages` for Stack Exchange.
- Updated existing collectors to consume the page iterators while preserving the current raw item and diagnostics outputs.
- Added tests for multi-page Hacker News and Stack Exchange collection interfaces.
- Reason: prepare for larger public API collection, batch processing, and resumable storage without turning the current pipeline into an unbounded in-memory crawler.
- Verification: `python -m unittest discover -s tests -v` passed with 34 tests; offline sample run `20260525_211135` completed with 5 raw items, 4 retained evidence candidates, and 0 fallback items.
- Next: add batch-level persistence for collected pages or implement run-comparison/dashboard views over the SQLite query layer.

### Page-Level Collection Persistence

- Added `collected_pages` to collector diagnostics.
- Added `collection_pages` table in SQLite.
- Added `get_collection_pages` in `src/storage/sqlite_store.py`.
- Stored source, query, page number, request metadata, raw count, retained page item count, and `has_more` for each collected API page.
- Reason: provide the first checkpoint layer for future resumable collection, batch processing, and larger public API runs.
- Verification: `python -m unittest discover -s tests -v` passed with 36 tests; offline sample run `20260525_211344` completed with 5 raw items, 4 retained evidence candidates, and 0 fallback items.
- Next: add explicit resumable collection state or move toward a small CLI command for inspecting stored runs.

### Resumable Collection State

- Added `CollectionState` in `src/models.py`.
- Added `collection_states` table in SQLite.
- Added `get_collection_states` in `src/storage/sqlite_store.py`.
- Aggregated page-level diagnostics into per-source/query state with page count, last page, next page, total raw count, total retained item count, and completion status.
- Reason: make future resumable collection explicit instead of inferring progress only from raw page rows.
- Verification: `python -m unittest discover -s tests -v` passed with 37 tests; offline sample run `20260525_211623` completed with 5 raw items, 4 retained evidence candidates, and 0 fallback items.
- Next: add a CLI command for inspecting stored runs and collection state, or implement live resume behavior using the stored next-page state.

### Run Inspection CLI

- Added `src/inspect_runs.py`.
- Added commands to list stored runs, inspect one run summary, inspect per-source/query collection state, and inspect ranked evidence rows with limit, offset, and optional category filtering.
- Added CLI regression coverage in `tests/test_baseline_pipeline.py`.
- Updated README and scale planning docs with the inspection workflow.
- Reason: make the SQLite run index useful before building dashboard views or live resume logic.
- Verification: `python -m unittest discover -s tests -v` passed with 38 tests; offline sample run `20260525_212051` wrote to SQLite; live smoke run `20260525_212107` was inspectable with collection state and ranked evidence rows.
- Next: implement live resume behavior using stored `next_page_number` state, then move to batch processing.

### Live Resume from Collection State

- Added `--resume-from-run-id` to the main pipeline CLI.
- Added `get_resume_start_pages` to the SQLite storage read layer.
- Updated Hacker News and Stack Exchange paginated collectors to accept source/query start pages while preserving their default first-page behavior.
- Added `resume_from_run_id` to run metadata and the SQLite run table, with a schema migration for existing local databases.
- Updated the inspection CLI to show the parent run ID for resumed runs.
- Reason: support larger live collection through bounded continuation instead of repeatedly starting at the first API page.
- Verification: `python -m unittest discover -s tests -v` passed with 40 tests; live resume run `20260525_212516` resumed from `20260525_212107`, collecting Hacker News page 1 and Stack Exchange page 2, then exposed next pages through `src/inspect_runs.py --collection-state`.
- Next: add cross-run deduplication or batch processing so resumed runs can be merged into larger analysis sets cleanly.

### Cross-Run Resume Deduplication

- Added `get_resume_lineage_run_ids` and `get_raw_item_source_keys` to the SQLite storage read layer.
- Added resume-chain raw item deduplication in `src/main.py` before quality filtering and relevance scoring.
- Skipped duplicates are written to `data/processed/<run_id>_cross_run_duplicate_items.json`.
- Added regression tests for lineage lookup, raw source-key lookup, and resume deduplication.
- Reason: keep resumed collection chains from re-analyzing the same public source item when API pages overlap or a run is repeated.
- Verification: `python -m unittest discover -s tests -v` passed with 42 tests; deterministic dedupe smoke run `20260525_212951` skipped 5 duplicate sample records from parent run `20260525_212051`.
- Next: add batch processing for filtering, relevance scoring, and signal extraction.

### Batch Filtering and Relevance Preparation

- Added `src/processors/batch_pipeline.py`.
- Added configurable `--processing-batch-size` with JSON config and environment support.
- Updated quality filtering and relevance preparation to preserve global source indexes and item IDs when processed in batches.
- Added per-run batch summaries at `data/processed/<run_id>_batch_summary.json`.
- Added `processing_batch_size` to run metadata, SQLite run summaries, the inspection CLI, and the example config.
- Reason: prepare for larger raw item volumes without changing the existing JSON, CSV, Markdown, HTML, or SQLite output shapes.
- Verification: `python -m unittest discover -s tests -v` passed with 43 tests; offline batch smoke run `20260525_213334` used batch size 2 and produced 3 batch summary rows with the expected 2/2/1 split.
- Next: persist intermediate batch stage outputs or add aggregate views across resumed run chains.

### SQLite Processing Batch Persistence

- Added a `processing_batches` table to SQLite.
- Added `get_processing_batches` to the storage read layer.
- Updated `save_run_to_sqlite` to persist per-batch status, raw item range, and stage counts.
- Updated `src/inspect_runs.py` with `--batches`.
- Reason: make batch progress inspectable from the database before adding interrupted-run recovery, parallel NLP/ML workers, or job orchestration.
- Verification: `python -m unittest discover -s tests -v` passed with 43 tests; offline smoke run `20260525_213759` stored 3 completed batch rows in SQLite with the expected 2/2/1 raw item split.
- Next: add aggregate views across resumed run chains or persisted per-batch artifacts for model outputs.

### Model Artifact Storage Layer

- Added a `model_artifacts` table to SQLite.
- Added `save_model_artifacts` and `get_model_artifacts` to the storage read/write layer.
- Added artifact filters for run ID, artifact type, batch index, limit, and offset.
- Updated `src/inspect_runs.py` with `--artifacts`, `--artifact-type`, and `--batch-index`.
- Reason: define a durable interface for future embeddings, classifiers, clustering labels, reranker outputs, and LLM summaries without coupling the pipeline to one model provider.
- Verification: `python -m unittest discover -s tests -v` passed with 45 tests; SQLite smoke wrote a `classification` artifact to run `20260525_213759` and inspected it through `src/inspect_runs.py --artifacts --artifact-type classification`.
- Next: add a deterministic baseline artifact producer before connecting external NLP/ML models.

### Deterministic Classification Artifacts

- Added `src/processors/model_artifacts.py`.
- Added deterministic `classification` artifacts for prepared items using the current heuristic relevance fields.
- Added per-item input hashes and batch-index mapping for generated artifacts.
- Updated `src/main.py` to write `data/processed/<run_id>_model_artifacts.json` and persist artifacts to SQLite.
- Reason: close the artifact production loop with a stable baseline before introducing embeddings, classifiers, or LLM calls.
- Verification: `python -m unittest discover -s tests -v` passed with 46 tests; offline smoke run `20260525_222259` generated 4 `heuristic-signal-classifier@v1` classification artifacts and exposed them through `src/inspect_runs.py --artifacts --artifact-type classification`.
- Next: add aggregate views across resumed run chains, then semantic grouping or embedding artifacts.

### Resume Chain Aggregate Views

- Added `get_run_chain_summary`, `get_run_chain_evidence_rows`, and `get_run_chain_model_artifacts` to the SQLite read layer.
- Added `src/inspect_runs.py --chain`, which can summarize a resumed run chain and combine with `--evidence` or `--artifacts`.
- Reason: make resumed collection behave like one larger logical acquisition job for inspection, dashboard queries, and future NLP/ML batch jobs.
- Verification: `python -m unittest discover -s tests -v` passed with 48 tests.
- Next: add semantic grouping or embedding artifacts over prepared evidence.

### Collection Policy Controls

- Added per-run collection controls for source enablement, API page size, maximum pages per query, Hacker News sort order, Stack Exchange sort/order, request timeout, source item limits, and downstream processing batch size.
- Updated Hacker News and Stack Exchange collectors to use the configured page policy instead of only deriving page behavior from total item limits.
- Stored the selected collection policy in run metadata and SQLite, and exposed it through `src/inspect_runs.py`.
- Reason: make large-scale acquisition tunable and auditable before adding local Streamlit controls or semantic NLP batch jobs.
- Verification: `python -m unittest discover -s tests -v` passed with 50 tests; offline smoke run `20260525_224200` preserved the configured collection policy in SQLite and `src/inspect_runs.py` output.
- Next: start semantic grouping or embedding artifacts.

### Deterministic Evidence Clusters

- Added deterministic `evidence_cluster` artifacts through `heuristic-evidence-clusterer@v1`.
- Cluster artifacts group prepared items by interpretable pain mechanisms such as customer-data sync, workflow automation reliability, setup/onboarding, manual admin burden, lean-team adoption burden, AI trust, and product complexity.
- Added `get_cluster_artifacts`, `get_run_chain_cluster_artifacts`, and `src/inspect_runs.py --clusters`.
- Updated the main pipeline to write `data/processed/<run_id>_cluster_artifacts.json` and persist clusters in SQLite through the existing model-artifact layer.
- Reason: create a stable pain-point grouping interface before introducing transformer embeddings or heavier NLP dependencies.
- Verification: `python -m unittest discover -s tests -v` passed with 52 tests; offline smoke run `20260525_224730` generated 3 evidence clusters and exposed them through `src/inspect_runs.py --clusters`.
- Next: add embedding artifacts or local Streamlit views over clusters.

### Lightweight Embedding Artifacts

- Added deterministic `embedding` artifacts through `hashed-text-embedding@v1`.
- Each prepared item now gets a sparse hashed text vector with dimensions, nonzero indices, normalized values, top terms, token count, and input hash.
- Added `get_embedding_artifacts`, `get_run_chain_embedding_artifacts`, and `src/inspect_runs.py --embeddings`.
- Updated the main pipeline to write `data/processed/<run_id>_embedding_artifacts.json` and persist embeddings in SQLite through the existing model-artifact layer.
- Reason: establish a stable embedding artifact interface before introducing transformer dependencies or heavier local NLP models.
- Verification: `python -m unittest discover -s tests -v` passed with 54 tests; offline smoke run `20260525_225153` generated 4 embedding artifacts and exposed them through `src/inspect_runs.py --embeddings`.
- Next: use embedding artifacts to improve cluster assignment, or start local Streamlit views over stored runs, embeddings, and clusters.

### Embedding-Assisted Cluster Assignment

- Upgraded `heuristic-evidence-clusterer` from `v1` to `v2`.
- Cluster assignment now uses pain-mechanism candidate buckets plus hashed-embedding cosine connected components.
- Cluster artifacts now record the grouping basis, similarity threshold, embedding model metadata, and similarity-to-representative scores.
- Added `docs/nlp_methodology.md` to document the NLP construction, principles, limitations, and transformer upgrade path.
- Reason: finish the first complete NLP layer while preserving provenance and avoiding a heavy model dependency before the artifact interface is stable.
- Verification: `python -m unittest discover -s tests -v` passed with 54 tests; offline smoke run `20260525_225711` generated 4 embedding artifacts, 3 embedding-assisted evidence clusters, and exposed cluster basis/threshold through `src/inspect_runs.py --clusters`.
- Next: either add a local transformer embedding option behind `embedding` artifacts or build local Streamlit views over the stored runs and clusters.

### Cluster-First Report Exports

- Updated Markdown and HTML exports to accept `evidence_cluster` artifacts and show a pain-point cluster section before category evidence sections.
- Added `output/csv/<run_id>_evidence_clusters.csv`.
- Updated the main pipeline to pass cluster artifacts into Markdown, HTML, and CSV exports.
- Reason: make reports useful for larger runs by presenting repeated pain mechanisms and representative evidence before listing category-level evidence.
- Verification: `python -m unittest discover -s tests -v` passed with 54 tests; offline smoke run `20260525_231551` generated 3 evidence clusters visible in Markdown, HTML, and cluster CSV outputs.
- Next: consider a local transformer embedding option behind the current artifact interface.

### Optional Transformer Embedding Backend

- Added `src/processors/embeddings.py` with a default hashing provider and an optional local sentence-transformer provider.
- Added `--embedding-backend`, `--embedding-model`, JSON config keys, and environment support.
- Updated embedding and cluster artifact generation to use the configured provider while keeping hashing as the default.
- Added `requirements-transformer.txt` for optional local transformer installs.
- Reason: allow heavier local semantic embeddings without changing storage, report, cluster, or inspection interfaces.
- Verification: `python -m unittest discover -s tests -v` passed with 55 tests; offline smoke run `20260525_232106` generated 4 hashing embedding artifacts, 3 clusters, and run metadata with `embedding_backend=hashing`.
- Next: tune transformer-backed clustering on reviewed examples.

### Cluster Evaluation Harness

- Added `samples/cluster_review_labels.json`.
- Added `src/evaluate_clusters.py` to evaluate predicted clusters against reviewed source-level labels.
- Added pairwise precision, recall, and F1 metrics for cluster quality.
- Parameterized `--cluster-similarity-threshold` through CLI, JSON config, and environment variables.
- Cluster artifacts now store full member item IDs and source IDs in addition to representative IDs.
- Reason: make clustering tunable and testable before expanding transformer-backed NLP.
- Verification: `python -m unittest discover -s tests -v` passed with 57 tests; `python src/evaluate_clusters.py --raw-items-file samples/small_business_operations_raw_items.json --labels-file samples/cluster_review_labels.json --embedding-backend hashing --cluster-similarity-threshold 0.12 --processing-batch-size 2` reported precision=1.0, recall=1.0, and F1=1.0 on the small reviewed sample.
- Next: expand reviewed labels with real run examples and compare hashing against a local sentence-transformer backend.

### Cluster Review Export

- Added `src/export_cluster_review.py`.
- The exporter creates `output/csv/<run_id>_cluster_review.csv` and `output/csv/<run_id>_cluster_review_labels.json` from a run's cluster artifacts and normalized items.
- Review rows include source ID, current cluster ID/key, editable reviewed label, source metadata, relevance score, URL, top terms, and text excerpt.
- Reason: make reviewed-label expansion practical before tuning thresholds or comparing embedding backends.
- Verification: `python -m unittest discover -s tests -v` passed with 59 tests; `python src/export_cluster_review.py --run-id 20260525_232531` exported 4 review rows across 3 clusters.
- Next: use review exports from larger live runs to build a stronger cluster-evaluation label set.

### Cluster Threshold Sweep Evaluation

- Added `--cluster-similarity-thresholds` to `src/evaluate_clusters.py`.
- The evaluator can now compare multiple thresholds in one run and select the best result by pairwise F1, recall, precision, and cluster count.
- Added `--output-csv` for threshold sweep summary rows.
- Reason: make threshold tuning repeatable once the reviewed label set grows.
- Verification: `python -m unittest discover -s tests -v` passed with 61 tests; `python src/evaluate_clusters.py --raw-items-file samples/small_business_operations_raw_items.json --labels-file samples/cluster_review_labels.json --embedding-backend hashing --cluster-similarity-thresholds "0.05;0.12;0.2" --processing-batch-size 2 --output-json output/csv/cluster_threshold_sweep_20260525_hashing.json --output-csv output/csv/cluster_threshold_sweep_20260525_hashing.csv` reported F1=1.0 for all three thresholds on the small sample.
- Next: expand reviewed labels and run threshold sweeps on a larger live-run review set.

### Cluster Backend Comparison

- Added `--embedding-backends` to `src/evaluate_clusters.py`.
- The evaluator can now compare multiple embedding backend specs across the same threshold list.
- Backend comparison outputs text, JSON, and flattened CSV rows.
- Reason: close the clustering-evaluation loop so hashing and transformer embeddings can be compared against the same reviewed labels.
- Verification: `python -m unittest discover -s tests -v` passed with 62 tests; `python src/evaluate_clusters.py --raw-items-file samples/small_business_operations_raw_items.json --labels-file samples/cluster_review_labels.json --embedding-backends "hashing;hashing:hashing-control" --cluster-similarity-thresholds "0.05;0.12;0.2" --processing-batch-size 2 --output-json output/csv/cluster_backend_comparison_20260525_hashing.json --output-csv output/csv/cluster_backend_comparison_20260525_hashing.csv` produced backend comparison JSON and CSV outputs.
- Next: expand reviewed labels with larger live-run examples, then run a real `hashing` versus `sentence-transformer` comparison after installing optional transformer dependencies.
