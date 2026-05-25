# Scale Strategy

This document records how the pipeline should evolve when it needs to collect and analyze substantially larger public datasets.

## Current Scale

The current baseline is a local, single-run pipeline. It is suitable for:

- Small live API runs.
- Deterministic offline demos.
- Regression tests.
- Portfolio-ready evidence memos.

It is not yet designed for unbounded collection, long-running crawls, or multi-million-record analysis.

## Scale Goals

Large-scale development should support:

- Many user-defined query families.
- Paginated public API collection.
- Incremental runs that resume cleanly.
- Deduplication across sources and runs.
- Batch filtering, relevance scoring, and signal extraction.
- Stored run metadata, diagnostics, raw items, processed items, and evidence rows.
- Dashboard review without loading every raw record into memory.

## Collection Architecture

Future collectors should move from one-shot retrieval to paginated source adapters.

Each source adapter should expose:

- Source identity and allowed endpoint metadata.
- Query parameters used for each request.
- Pagination cursor or page number.
- Rate-limit and retry diagnostics.
- Raw response references when debug capture is enabled.
- Stable source IDs for deduplication.

Collection should remain API-based and provenance-preserving. Do not introduce broad web scraping or private-source collection to solve scale.

## Storage Architecture

For larger runs, file exports should remain artifacts, but storage should move into tables.

Suggested local-first path:

- SQLite for local research runs and dashboard demos.
- Separate tables for runs, collector diagnostics, raw items, prepared items, excluded items, relevance-excluded items, evidence rows, and category summaries.
- Unique constraints on source name plus source ID to support deduplication.
- Indexes on run ID, source type, query theme, category, relevance score, fallback status, and created timestamp.

If the project grows beyond local research, the same schema can move toward Postgres or a managed analytical store.

## Processing Architecture

Large-scale analysis should be batch-oriented.

Recommended shape:

- Collect raw items in pages.
- Write each page before processing.
- Process raw items in batches.
- Store intermediate outputs after each stage.
- Recompute analysis from stored prepared items and evidence rows.
- Keep exports as final artifacts, not the primary database.

Avoid designing the dashboard around loading all raw items, prepared items, and evidence rows into one process at once.

## NLP and ML at Scale

Semantic clustering and embeddings should run as explicit batch jobs. The current baseline writes `embedding` and `evidence_cluster` artifacts and now supports both the default lightweight hashing backend and an optional local sentence-transformer backend.

Recommended sequence:

- Start with deterministic filtering and relevance scoring. Completed.
- Add lightweight embedding artifacts over prepared items. Completed.
- Add pain-mechanism and embedding-similarity cluster artifacts over prepared items. Completed.
- Add local transformer embedding generation for retained prepared items. Initial adapter completed.
- Evaluate cluster quality against reviewed source-level labels before changing thresholds or models.
- Export cluster review files so humans can create more labels from real runs.
- Compare threshold sweeps before adopting a new clustering threshold.
- Compare embedding backends against the same reviewed labels before switching defaults.
- Store embeddings or embedding references separately.
- Cluster per run or per venture category.
- Keep representative source-linked evidence for every cluster.

LLM-assisted summarization should summarize stored clusters or selected evidence rows, not raw unbounded source streams.

## Operational Limits

Every large-scale run should record:

- Source-specific item limits.
- Source enablement flags.
- API page size.
- Maximum pages per query.
- Source sort order.
- Request timeout.
- Pagination depth.
- Query family.
- Start and end timestamps.
- Fallback count.
- Exclusion counts.
- Deduplication counts.
- Rate-limit and failure diagnostics.

Large-scale collection should have explicit limits by default. Unbounded collection is out of scope.

## Near-Term Implementation Path

1. Add empty-output and edge-case tests. Completed.
2. Add SQLite storage behind the existing JSON/CSV outputs. Completed.
3. Add a run index so prior runs can be listed and compared. Initial implementation completed.
4. Add paginated collection interfaces for each source. Initial implementation completed.
5. Add batch-level persistence or resumable run state for collected pages. Initial page-level persistence completed.
6. Add explicit resumable collection state. Completed.
7. Add a read-only CLI for inspecting stored runs, collection state, and evidence rows. Completed.
8. Add live resume behavior using stored next-page state. Completed.
9. Add source-key deduplication across resumed run chains. Completed.
10. Process items in batches while preserving the current analysis output shape. Completed.
11. Persist processing batch status and stage counts in SQLite. Completed.
12. Add a generic SQLite model artifact layer. Completed.
13. Add deterministic baseline artifact producers. Completed.
14. Add aggregate views across resumed run chains. Completed.
15. Add configurable collection-policy controls for page size, page depth, sort order, and source enablement. Completed.
16. Add evidence-cluster artifacts over prepared evidence. Completed.
17. Add lightweight embedding artifacts over prepared evidence. Completed.
18. Use embedding artifacts to improve cluster assignment. Completed.
19. Add a local transformer embedding option behind the existing artifact interface. Initial adapter completed.
20. Add a cluster evaluation harness with reviewed labels. Initial implementation completed.
21. Add cluster review export for human labeling. Initial implementation completed.
22. Add threshold sweep support for cluster evaluation. Completed.
23. Add backend comparison support for cluster evaluation. Completed.
24. Add dashboard views that query summaries and paginated evidence tables.
