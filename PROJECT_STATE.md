# Project State

## Current Project Objective

Build a lightweight, credible MVP of an AI-assisted community signal pipeline for early-stage venture-category evaluation.

The project now demonstrates how messy public discussion and public software feedback signals can be transformed into structured supplementary evidence for uncertainty-aware human decision-making. The current category scope is AI-enabled tools for small-business operations, lean teams, solo operators, and one-person companies.

## Current Repo Status

- Repository path: `C:\Users\zhiwe\Desktop\projects\ai_assisted_community_signal_pipeline\ai-assisted-community-signal-pipeline`
- Git state: initialized Git repository.
- Current branch: `main`.
- Commit status at MVP implementation time: no commits yet.
- Project memory files exist: `AGENT.md` and `PROJECT_STATE.md`.
- MVP files have been added under `src/`, `docs/`, `data/`, and `output/`.

## What Has Already Been Implemented

Implemented MVP components:

- Public discussion collector for Hacker News comments through the Algolia API.
- Public implementation-feedback collector for Stack Overflow public questions through the Stack Exchange API.
- Venture-category query family for small-business operations, admin automation, CRM/workflow frustration, and solo-operator/lean-team pain.
- Built-in fallback records so the demo still runs when public endpoints are unavailable.
- Text cleaning and normalization.
- Source-aware text-quality filtering that excludes likely job postings, career pages, promotional copy, product landing-page summaries, and generic directory/listing snippets.
- Heuristic weak-signal extraction for problems, unmet needs, adoption barriers, dissatisfaction, differentiation opportunities, demand clues, and competitor mentions.
- Evidence relevance scoring and section-specific ranking for stronger category alignment.
- Venture signal analyzer that creates a structured support memo without investment recommendations.
- CSV, Markdown, static HTML, raw JSON, and processed JSON exports.
- Excluded-item logs with explicit exclusion reasons in JSON and CSV.
- Live retrieval diagnostics that log endpoint, query, live item count, fallback status, failure reason, and final fallback count.
- Debug raw-response files: `data/raw/latest_source1_raw.json`, `data/raw/latest_source2_raw.json`, and per-run collector diagnostics JSON.
- README and docs covering product framing, decisions, and roadmap.
- Verified local run produced CSV, Markdown, HTML, raw JSON, and processed JSON outputs.

## Current Data Sources Selected

Current MVP data sources:

- Source Type 1: Hacker News public comments via the Algolia API.
- Source Type 2: Stack Overflow public questions via the Stack Exchange API.

These sources were selected because they are public, developer-friendly, practical for a working demo, and relevant to weak-signal venture evaluation for early-stage AI software, business operations tools, and digital productivity systems for lean teams.

Future data sources must continue to comply with the boundaries in `AGENT.md`, especially:

- Publicly accessible or clearly community-visible sources only.
- No private groups, private chats, restricted repositories, or unauthorized private profiles.
- No paywalled scraping or access-control bypassing.
- No private personal data enrichment.
- No unlawful, deceptive, or terms-violating collection.
- No Reddit data source for this MVP.

## Key Substantive Findings So Far

- The repo was originally empty except for Git metadata and project memory files.
- Building in the existing repo was better than creating a sibling repo because there was no conflicting implementation.
- Hacker News Algolia comments are a practical non-Reddit discussion source for technical community weak signals.
- GitHub was tested as Source 2 after Apple App Store reviews, but local testing showed unreliable live retrieval and read timeouts.
- Stack Overflow replaced GitHub as Source 2 because the Stack Exchange API is more practical for live retrieval and directly surfaces implementation barriers, setup friction, integration problems, and operational-tool constraints.
- Scope was tightened away from a narrow meeting-notes product theme toward a venture-category analysis of AI-enabled small-business operations tools.
- Default community query family: `small business workflow pain`, `admin automation frustration`, `CRM frustration small business`, `solo founder automation`.
- Default Stack Overflow query family: `workflow automation integration`, `crm api integration problem`, `zapier automation error`, `n8n setup issue`.
- The MVP can run without third-party Python dependencies.
- The generated memo is explicitly supplementary evidence, not an invest/do-not-invest score.
- Provenance, source linkage, and uncertainty notes are implemented as first-class report elements.
- Evidence quality is now prioritized over evidence quantity through filtering before signal extraction.
- Evidence ranking now prioritizes small-business operations, workflow friction, admin burden, setup/onboarding pain, integration problems, operational software complexity, and lean-team or solo-operator constraints.
- Verification run `20260524_163624` completed successfully with 8 fallback demo items and 31 extracted evidence rows because live public endpoints were unavailable from the sandbox.
- Escalated live network verification was attempted but the permission review timed out, so live endpoint verification remains a local follow-up.
- Quality-filter verification run `20260525_070029` completed successfully with 8 raw fallback items, 0 filtered fallback items, 8 evidence candidates, and filtering logs in JSON and CSV.
- A synthetic sanity check excluded a job posting and promotional platform copy while retaining a complaint-style customer review.
- Current debugging focus: validate whether live Hacker News Algolia and Stack Exchange API endpoints can be reached from the user's local environment and inspect raw responses when they cannot.
- Debug run `20260525_072423` showed both live requests failing before response parsing with Windows socket permission error `WinError 10013`; both sources were classified as `endpoint_unavailable` and fallback inserted 8 total records.
- A second elevated live validation attempt was requested after the user asked to try again, but the approval review timed out before network access could be granted.
- Source 2 replacement verification run `20260525_081253` used GitHub repository `microsoft/vscode` with query `setup`; sandbox socket restrictions still produced `endpoint_unavailable`, but logs, diagnostics, fallback labeling, Markdown, HTML, and CSV generation all worked with the GitHub collector.
- Scope-tightening verification run `20260525_090846` used the venture-category defaults for AI-enabled small-business operations tools, generated category-level Markdown/HTML/CSV outputs, and showed the new query families in terminal diagnostics and report metadata.
- Final GitHub reliability pass replaced Source 2 search with direct recent-issues retrieval from `https://api.github.com/repos/n8n-io/n8n/issues`, then issue-comment retrieval. It uses `requests.Session()`, GitHub JSON headers, 25-second timeout, and 2 retries with short backoff.
- Verification run `20260525_100913` still failed in the sandbox with `WinError 10013`, meaning the environment denied outbound socket access before GitHub could respond. This does not prove the endpoint strategy is invalid; it indicates this runtime cannot open the network socket.
- GitHub Source 2 was then retired because local testing still showed zero live issues/comments and read timeouts. Source 2 is now Stack Overflow public questions via `https://api.stackexchange.com/2.3/search/advanced`.
- Stack Overflow replacement verification run `20260525_103508` generated Markdown/HTML/CSV outputs with Stack Exchange metadata and query-family logging. In the Codex sandbox, outbound sockets are still blocked with `WinError 10013`, so local user testing outside the sandbox is needed to confirm live Stack Exchange records.
- Evidence relevance improvement run `20260525_111900` added relevance scores, signal-level ranking, and `relevance_excluded_items.json`; section examples now show strongest evidence first with scores.
- Evidence relevance pass `20260525` strengthened ranking toward small-business operations, workflow fragmentation, admin burden, onboarding/setup friction, integration pain, switching cost, poor operational-tool fit, and lean-team or solo-operator constraints. It also down-ranks low-level engineering/debugging text when there is weak business-workflow context.
- Default retrieval targets were moderately expanded from 25 to 50 items per source, for an intended live raw sample of roughly 100 items before quality and relevance filtering.
- Final GitHub-readiness pass strengthened exclusion/down-ranking for founder launch announcements, self-promotional product mentions, link-drop style evidence, and engineering-heavy debugging text with weak venture-category relevance. README was rewritten for clearer GitHub and PhD portfolio presentation.
- Final evidence precision pass added stricter context-anchor requirements, cultural/quote-reference exclusion, stricter discussion-source relevance checks, and unmet-needs filtering that requires concrete business, workflow, tool, integration, or operational context.
- Local live verification run `20260525_190705` succeeded with real public API data: 46 Hacker News discussion items, 46 Stack Overflow question items, 92 raw items total, 77 quality-filtered candidates, 65 relevance-filtered items retained for analysis, 163 extracted evidence rows, and 0 fallback items.
- Current baseline was reviewed as a modular prototype: collectors, processors, analyzer, exporters, and config are separated, but cross-module data contracts are still loose dictionaries and there is no test suite.
- `AGENT.md` was updated with next-phase development boundaries and technical hardening priorities.
- `docs/development_plan.md` was added to record the roadmap for backend hardening, custom user queries, NLP/ML improvements, dashboard work, storage, and evaluation.
- Initial regression test suite was added in `tests/test_baseline_pipeline.py`, covering text cleaning, quality filtering, relevance preparation, analyzer guardrails, exporters, and collector mapping functions.
- CLI configuration tests were added for CLI-over-env precedence, environment fallback behavior, and built-in defaults. Verification command `python -m unittest discover -s tests -v` passed with 12 tests.
- CLI argument support was added through `PipelineConfig.from_args()`. Users can now pass `--theme`, `--community-queries`, `--stackexchange-queries`, source limits, timeout, Stack Exchange site, and debug raw-output flags directly at runtime. Precedence is CLI arguments, then environment variables, then built-in defaults.
- CLI verification run `20260525_195340` succeeded with `--theme "CLI smoke test for small business automation"`, one Hacker News query, one Stack Overflow query, 2 items per source, 4 raw live items, 3 quality-filtered candidates, 3 relevance-filtered items, 0 fallback items, and run metadata preserving the CLI inputs.
- Initial dataclass contracts were added in `src/models.py` for `PreparedItem` and `EvidenceRow`. `prepare_items` and `analyze_venture_signals` now use those contracts internally while preserving the existing dict-shaped JSON, CSV, Markdown, and HTML outputs.
- Model contract tests were added for prepared item and evidence row export shapes. Verification command `python -m unittest discover -s tests -v` passed with 14 tests.
- Dataclass smoke run `20260525_195649` succeeded with live API data, 1 item per source, 2 raw items, 2 retained items, and 0 fallback items.
- Hacker News collection now uses 3-attempt retry behavior for HTTP, URL, timeout, and JSON parsing failures, matching the Stack Exchange collector's reliability pattern.
- README source-role documentation was expanded: Hacker News is framed as public market/problem-language evidence, while Stack Overflow is framed as implementation-friction and adoption-barrier evidence.
- Retry smoke run `20260525_203401` succeeded with live API data, 1 Hacker News item, 1 Stack Overflow item, 2 raw items, 2 retained items, and 0 fallback items.
- JSON config-file support was added through `--config`, with reusable example config at `configs/example_run.json`. Configuration precedence is now CLI arguments, JSON config file, environment variables, then built-in defaults.
- Config-file tests were added for config-over-env and CLI-over-config precedence. Verification command `python -m unittest discover -s tests -v` passed with 17 tests.
- Config smoke run `20260525_203759` succeeded using `configs/example_run.json` with CLI source-limit overrides, 1 Hacker News item, 1 Stack Overflow item, 2 raw items, 1 relevance-retained item, and 0 fallback items.
- Deterministic local raw-item input was added through `--raw-items-file`, which skips live collectors and runs the same quality filtering, relevance scoring, analysis, and export path on a JSON list of raw items.
- Sample raw items were added at `samples/small_business_operations_raw_items.json` for offline demos and regression checks.
- Local raw-item tests were added for file loading and source-count diagnostics. Verification command `python -m unittest discover -s tests -v` passed with 19 tests.
- Offline sample run `20260525_204202` succeeded with 5 sample raw items, 1 quality-filtered job item, 4 retained evidence candidates, 4 relevance-retained items, and 0 fallback items.
- Collector fallback handling was narrowed so Hacker News only falls back for HTTP, URL, timeout, and JSON/parsing failures, while Stack Exchange only falls back for request and JSON/parsing failures. Programming errors now propagate instead of being reported as source fallback.
- Collector behavior tests were added for timeout fallback and programming-error propagation for both live collectors. Verification command `python -m unittest discover -s tests -v` passed with 23 tests.
- Offline smoke run `20260525_204414` succeeded after the collector error-handling change with 5 sample raw items, 1 quality-filtered job item, 4 retained evidence candidates, 4 relevance-retained items, and 0 fallback items.
- Runtime `print` calls in `main.py` and collectors were replaced with standard-library `logging`, keeping terminal output readable while avoiding direct collector output during unit tests.
- `docs/development_log.md` was added as the chronological record of completed development steps, reasons, verification, and likely next steps.
- Runtime logging verification passed with `python -m unittest discover -s tests -v` covering 23 tests, no remaining `print(...)` calls in `src` or `tests`, and offline smoke run `20260525_204847` with 5 sample raw items, 4 retained evidence candidates, and 0 fallback items.
- `RawItem` and `CollectorDiagnostics` contracts were added in `src/models.py`, and collector/local-file paths now emit raw records and diagnostics through those contracts while preserving dict-shaped JSON and report outputs.
- Contract verification passed with `python -m unittest discover -s tests -v` covering 25 tests and offline smoke run `20260525_205243` with 5 sample raw items, 4 retained evidence candidates, and 0 fallback items.
- `FilteringSummary` was added in `src/models.py`, and the quality filter now emits report/dashboard statistics through that contract while preserving dict-shaped JSON and report outputs.
- Filtering summary contract verification passed with `python -m unittest discover -s tests -v` covering 26 tests and offline smoke run `20260525_205422` with 5 sample raw items, 4 retained evidence candidates, and 0 fallback items.
- `RunMetadata`, `VolumeSummary`, `RelevanceSummary`, and `AnalysisResult` were added in `src/models.py`. The analyzer now emits a complete contract-backed analysis result, and `main.py` passes filtering and relevance summaries into the analyzer instead of mutating the analysis dict after creation.
- Analysis contract verification passed with `python -m unittest discover -s tests -v` covering 28 tests and offline smoke run `20260525_205658` with 5 sample raw items, 4 retained evidence candidates, and 0 fallback items.
- Empty-output tests were added for zero raw input and empty analysis exports, confirming CSV, Markdown, and HTML outputs still generate when no evidence rows exist.
- `docs/scale_strategy.md` was added, and scale boundaries were recorded in `AGENT.md` and `docs/development_plan.md`: large-scale collection should use public API pagination, explicit limits, durable storage, deduplication, and batch processing rather than an unbounded in-memory crawl.
- Empty-output and scale-strategy verification passed with `python -m unittest discover -s tests -v` covering 30 tests and offline smoke run `20260525_210128` with 5 sample raw items, 4 retained evidence candidates, and 0 fallback items.
- SQLite storage was added in `src/storage/sqlite_store.py`, with local run indexing at `data/storage/pipeline_runs.sqlite3`.
- Each run now stores run metadata, collector diagnostics, raw items, prepared items, excluded items, relevance-excluded items, evidence rows, and category summaries in separate SQLite tables while preserving existing JSON, CSV, Markdown, and HTML exports.
- `source_id` was added to evidence rows to improve provenance and storage queries.
- SQLite verification passed with `python -m unittest discover -s tests -v` covering 31 tests and offline smoke run `20260525_210530`; database inspection confirmed 5 raw items and 20 evidence rows for that run.
- SQLite query helpers were added: `list_runs`, `get_run_summary`, and `get_evidence_rows`.
- Query helper verification passed with `python -m unittest discover -s tests -v` covering 32 tests and offline smoke run `20260525_210730`; direct query helper smoke check returned latest runs and top evidence rows from `data/storage/pipeline_runs.sqlite3`.
- Paginated collector interfaces were added through `CollectedPage`, `iter_discussion_pages`, and `iter_review_pages`.
- The existing Hacker News and Stack Exchange collectors now consume page iterators while preserving current item, diagnostics, fallback, JSON, CSV, Markdown, HTML, and SQLite outputs.
- Pagination verification passed with `python -m unittest discover -s tests -v` covering 34 tests and offline smoke run `20260525_211135` with 5 sample raw items, 4 retained evidence candidates, and 0 fallback items.
- Page-level collection persistence was added through `collected_pages` diagnostics and a SQLite `collection_pages` table.
- `get_collection_pages` was added to `src/storage/sqlite_store.py` so future CLI/dashboard code can inspect page-level collection state without reading raw diagnostics JSON directly.
- Page persistence verification passed with `python -m unittest discover -s tests -v` covering 36 tests and offline smoke run `20260525_211344` with 5 sample raw items, 4 retained evidence candidates, and 0 fallback items. Offline raw-file runs do not create collection-page rows because they skip live page adapters.
- Explicit resumable collection state was added through `CollectionState`, a SQLite `collection_states` table, and `get_collection_states`.
- Collection state aggregates page-level diagnostics by source and query, recording page count, last page, next page, total raw count, total retained item count, and completion status.
- Resumable-state verification passed with `python -m unittest discover -s tests -v` covering 37 tests and offline smoke run `20260525_211623` with 5 sample raw items, 4 retained evidence candidates, and 0 fallback items.
- A read-only inspection CLI was added at `src/inspect_runs.py`.
- The inspection CLI can list stored runs, show a single run summary, show per-source/query collection state, and show paginated ranked evidence rows from SQLite.
- Inspection CLI verification passed with `python -m unittest discover -s tests -v` covering 38 tests, offline sample run `20260525_212051`, and live smoke run `20260525_212107` inspectable through `--collection-state` and `--evidence`.
- Live resume was added through `--resume-from-run-id`.
- `get_resume_start_pages` now reads unfinished per-source/query `next_page_number` values from SQLite, and both live collectors can start from those stored page numbers.
- Resumed runs persist `resume_from_run_id` in run metadata and SQLite.
- Live resume verification passed with `python -m unittest discover -s tests -v` covering 40 tests and live run `20260525_212516`, which resumed from `20260525_212107` at Hacker News page 1 and Stack Exchange page 2.
- Cross-run deduplication was added for resumed run chains.
- `get_resume_lineage_run_ids` and `get_raw_item_source_keys` now read parent-chain run IDs and prior `source_name + source_id` keys from SQLite.
- `main.py` skips raw items already seen in the resume chain before quality filtering, relevance scoring, analysis, and SQLite raw-item persistence.
- Skipped duplicate records are written to `data/processed/<run_id>_cross_run_duplicate_items.json`.
- Cross-run deduplication verification passed with `python -m unittest discover -s tests -v` covering 42 tests and deterministic dedupe smoke run `20260525_212951`, which skipped 5 duplicate sample records from parent run `20260525_212051`.
- Batch filtering and relevance preparation were added through `src/processors/batch_pipeline.py`.
- `--processing-batch-size` is now supported through CLI, JSON config, and environment variables.
- Batch processing preserves global source indexes and prepared item IDs, writes `data/processed/<run_id>_batch_summary.json`, and keeps existing output shapes.
- Batch processing verification passed with `python -m unittest discover -s tests -v` covering 43 tests and offline smoke run `20260525_213334`, which processed 5 sample records in 3 batches with a 2/2/1 split.
- SQLite processing batch persistence was added through a `processing_batches` table and `get_processing_batches`.
- `src/inspect_runs.py --batches` now shows batch status, raw item range, and stage counts.
- SQLite batch persistence verification passed with `python -m unittest discover -s tests -v` covering 43 tests and offline smoke run `20260525_213759`, which stored 3 completed batch rows in SQLite with the expected 2/2/1 split.
- A generic model artifact storage layer was added through a `model_artifacts` table.
- `save_model_artifacts` and `get_model_artifacts` now support storing and querying model outputs by run ID, artifact type, batch index, limit, and offset.
- `src/inspect_runs.py --artifacts` can inspect stored artifacts with optional `--artifact-type` and `--batch-index` filters.
- Model artifact storage verification passed with `python -m unittest discover -s tests -v` covering 45 tests and a SQLite smoke artifact written to run `20260525_213759`.
- Deterministic classification artifacts were added through `src/processors/model_artifacts.py`.
- The main pipeline now writes `data/processed/<run_id>_model_artifacts.json` and persists `classification` artifacts to SQLite using `heuristic-signal-classifier@v1`.
- Deterministic artifact verification passed with `python -m unittest discover -s tests -v` covering 46 tests and offline smoke run `20260525_222259`, which generated 4 classification artifacts.
- Resume-chain aggregate views were added to the SQLite read layer through `get_run_chain_summary`, `get_run_chain_evidence_rows`, and `get_run_chain_model_artifacts`.
- `src/inspect_runs.py --chain` now shows aggregate counts across a run and its resume parents, and can combine with `--evidence` or `--artifacts` to inspect chain-wide evidence and model outputs.
- Resume-chain aggregate verification passed with `python -m unittest discover -s tests -v` covering 48 tests.
- Collection-policy controls were added for source enablement, per-source API page size, maximum pages per query, Hacker News sort order, Stack Exchange sort/order, request timeout, source item limits, and downstream processing batch size.
- The selected collection policy is now preserved in run metadata, SQLite, and `src/inspect_runs.py` output, making larger acquisition runs auditable.
- Collection-policy verification passed with `python -m unittest discover -s tests -v` covering 50 tests and offline smoke run `20260525_224200`, which showed the configured collection policy in `src/inspect_runs.py` output.
- Evidence-cluster artifacts were added through `heuristic-evidence-clusterer@v2`.
- The main pipeline now writes `data/processed/<run_id>_cluster_artifacts.json` and persists `evidence_cluster` artifacts in SQLite through the existing model-artifact layer.
- `src/inspect_runs.py --clusters` can inspect pain-point clusters, including labels, item counts, representative item IDs, top terms, source mix, and product-opportunity hints.
- Deterministic cluster verification passed with `python -m unittest discover -s tests -v` covering 52 tests and offline smoke run `20260525_224730`, which generated 3 evidence clusters visible through `src/inspect_runs.py --clusters`.
- Lightweight embedding artifacts were added through `hashed-text-embedding@v1`.
- The main pipeline now writes `data/processed/<run_id>_embedding_artifacts.json` and persists `embedding` artifacts in SQLite through the existing model-artifact layer.
- `src/inspect_runs.py --embeddings` can inspect prepared-item embedding artifacts, including vector dimensions, stored value count, token count, top terms, and model version.
- Lightweight embedding verification passed with `python -m unittest discover -s tests -v` covering 54 tests and offline smoke run `20260525_225153`, which generated 4 embedding artifacts visible through `src/inspect_runs.py --embeddings`.
- Cluster assignment now uses pain-mechanism candidate buckets plus hashed-embedding cosine connected components.
- Cluster artifacts preserve grouping basis, similarity threshold, embedding model metadata, and similarity-to-representative scores.
- `docs/nlp_methodology.md` documents the current NLP construction, principles, limitations, and transformer upgrade path.
- Embedding-assisted cluster verification passed with `python -m unittest discover -s tests -v` covering 54 tests and offline smoke run `20260525_225711`, which generated 3 embedding-assisted evidence clusters visible through `src/inspect_runs.py --clusters`.
- Markdown and HTML reports now show pain-point clusters before category evidence sections, and CSV output includes `<run_id>_evidence_clusters.csv`.
- Cluster-first report verification passed with `python -m unittest discover -s tests -v` covering 54 tests and offline smoke run `20260525_231551`, which generated 3 evidence clusters visible in Markdown, HTML, and CSV outputs.
- A configurable embedding provider layer was added in `src/processors/embeddings.py`.
- The default backend remains `hashed-text-embedding@v1`, and an optional local `sentence-transformer-embedding@v1` backend can be enabled with `--embedding-backend sentence-transformer`.
- Embedding backend and model can now be set through CLI, JSON config, or environment variables.
- Optional transformer dependency installation is documented in `requirements-transformer.txt`.
- Transformer-adapter verification passed with `python -m unittest discover -s tests -v` covering 55 tests and offline smoke run `20260525_232106`, which generated hashing embeddings and clusters through the provider interface.
- Cluster similarity threshold is now configurable through CLI, JSON config, and environment variables.
- `samples/cluster_review_labels.json` and `src/evaluate_clusters.py` were added for reviewed-label cluster evaluation.
- Cluster artifacts now include full member item IDs and source IDs in addition to representative IDs.
- Cluster evaluation verification passed with `python -m unittest discover -s tests -v` covering 57 tests and a small sample evaluation that reported precision=1.0, recall=1.0, and F1=1.0 for hashing at threshold 0.12.
- `src/export_cluster_review.py` was added to export human-review CSV rows and editable label-template JSON from existing run artifacts.
- Cluster review export verification passed with `python -m unittest discover -s tests -v` covering 59 tests and `python src/export_cluster_review.py --run-id 20260525_232531`, which exported 4 review rows across 3 clusters.
- `src/evaluate_clusters.py` now supports `--cluster-similarity-thresholds` to compare multiple thresholds in one run and `--output-csv` for sweep summary rows.
- Threshold sweep verification passed with `python -m unittest discover -s tests -v` covering 61 tests and a sample sweep over `0.05;0.12;0.2`, which reported F1=1.0 for all three thresholds on the small reviewed sample and wrote JSON plus CSV outputs.
- `src/evaluate_clusters.py` now supports `--embedding-backends` for backend comparison across the same threshold list.
- Backend comparison verification passed with `python -m unittest discover -s tests -v` covering 62 tests and a sample comparison that produced JSON plus CSV outputs.

## Limitations Discovered So Far

- The extraction logic is heuristic and transparent, not a trained or validated NLP model.
- The text-quality filter is heuristic and may exclude some useful edge cases; its reason logs should be reviewed after live runs.
- The current fallback dataset is intentionally user-like, so it does not demonstrate many exclusions by itself; live runs or synthetic checks are better for inspecting exclusion behavior.
- Hacker News is biased toward technical audiences.
- Stack Overflow questions skew toward technical users and implementation-facing problems, so they should be interpreted as evidence of practical barriers rather than full market demand.
- Live public endpoints may fail due to connectivity, rate limits, or source-side changes, so fallback demo records are included.
- No formal benchmark or human evaluation workflow exists yet.
- No frontend framework exists; output is static HTML by design.
- The current implementation now has typed contracts for raw items, prepared items, evidence rows, collector diagnostics, filtering summaries, relevance summaries, run metadata, volume summaries, and analysis results. Run config is still a dataclass but not part of the shared model contract module.
- Collector diagnostics now have a typed contract, but the exported diagnostics JSON is still intentionally dict-shaped for compatibility.
- The current execution model is still mostly a local run-triggered pipeline, but run outputs now persist to SQLite, can resume live collection from prior page state, can skip duplicate raw items across a resume chain, can process filtering/relevance preparation in configurable batches, records batch status in SQLite, stores deterministic classification, configurable embedding, and embedding-assisted evidence-cluster artifacts, exposes cluster-first Markdown/HTML/CSV reports, exports cluster review files for human labeling, exposes cluster evaluation metrics, threshold sweeps, and backend comparisons for reviewed labels, exposes aggregate resume-chain views, and preserves collection-policy controls. Large-scale support still needs transformer-backed clustering tuning on larger reviewed samples, stronger job orchestration, and dashboard/query ergonomics before attempting very large NLP/ML collection or clustering jobs.

## Important Design Decisions Already Made

- `AGENT.md` is the stable source of truth for project boundaries and operating rules.
- `PROJECT_STATE.md` is the evolving source of truth for current progress and handoff notes.
- Future assistants should read both files before making substantive changes.
- The project must preserve evidence provenance from ingestion through reporting.
- The pipeline should remain modular across ingestion, normalization, signal extraction, scoring, and report generation.
- The project should support human review and diligence preparation, not automated investment decisions.
- The MVP should combine one public discussion source and one public review/feedback source.
- Reddit must not be used as a data source.
- The first implementation should stay lightweight and beginner-friendly.
- Static HTML, Markdown, and CSV outputs are sufficient for the MVP.
- Evidence candidates should look like user discussion, customer review, complaint, comparison, or first-person experience text.
- The memo should read as supplementary evidence for evaluating a venture category under uncertainty, not a review of one app.
- The current system should be described as a public API collection, heuristic NLP, relevance scoring, and report-generation baseline, not as a trained ML or predictive system.
- Future NLP or ML should improve evidence quality, semantic grouping, classification, summarization, or uncertainty support, not produce investment predictions.
- Custom user query support should preserve the full run configuration so outputs remain auditable.
- Large-scale data collection should be explicit, bounded, resumable, and API-based; unbounded scraping or one-process in-memory collection is out of scope.
- Page-level collector interfaces, page-level persistence, explicit per-source/query collection state, a read-only inspection CLI, live resume from prior page state, resume-chain source-key deduplication, batch filtering/relevance preparation, SQLite batch status persistence, generic model artifact storage, deterministic classification artifacts, configurable embedding artifacts, embedding-assisted evidence-cluster artifacts, cluster-first report exports, cluster review export, cluster evaluation with threshold sweeps and backend comparisons, resume-chain aggregate views, and configurable collection policies now exist, but collection is still run-triggered and is not yet a background job.

## Open Problems

- Expand tests for collectors, processors, analyzers, exporters, and future storage behavior beyond the current baseline coverage.
- Expand reusable run configuration support if named presets or multiple config files become useful.
- Add a small dashboard or CLI view on top of the SQLite query helpers.
- Expand reviewed cluster labels and tune the local transformer embedding option behind the current embedding artifact interface.
- Review excluded-item logs after live runs and tune filter rules where they are too strict or too permissive.
- Inspect relevance-filtered logs after live runs to confirm that pure technical debugging and generic enterprise complaints are being down-ranked without losing useful implementation-friction evidence.
- Add optional LLM-assisted summarization while preserving evidence snippets.
- Continue expanding the curated deterministic sample dataset if more demo scenarios are needed.
- Define a small human evaluation rubric for usefulness and traceability.
- When running outside the sandbox with internet access, confirm that the live Hacker News and Stack Exchange endpoints return fresh public records.
- If live endpoints succeed, update this file with the run ID, item counts, and any source-specific issues discovered.

## Next Recommended Actions

1. Commit the current verified MVP and documentation updates once reviewed.
2. Expand reviewed cluster labels and tune the local transformer embedding option behind the existing embedding artifact interface.
3. Add local Streamlit views over stored runs, evidence, embeddings, and clusters.
4. Consider Streamlit as the fastest dashboard MVP, then FastAPI plus React if the project needs a more production-like architecture.
5. Consider optional LLM-assisted summarization after the heuristic baseline is stable and evaluation examples exist.
6. Update `PROJECT_STATE.md` and `docs/development_log.md` after each substantive development step.

## Handoff Notes for Future AI or Code Assistant Sessions

Future assistants should start by reading `AGENT.md` and this file.

Use `AGENT.md` to understand fixed project boundaries:

- What the project is.
- What the project is not.
- What data sources are allowed or disallowed.
- What architectural and documentation rules must be respected.

Use `PROJECT_STATE.md` to understand current progress:

- What has already happened.
- What has been tried.
- What worked or failed.
- What remains open.
- What should happen next.

Before implementing new functionality, update or confirm the relevant project state here. After implementing substantive changes, record what changed, what was learned, what remains uncertain, and what the next assistant should do.
