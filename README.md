# AI-Assisted Community Signal Pipeline for Early-Stage Venture Evaluation

A lightweight prototype for AI-assisted, uncertainty-aware venture-evaluation support. The project turns messy public discussion and public software feedback into structured supplementary evidence for early-stage diligence.

The problem it addresses: early-stage ventures often lack rich formal data, but public communities and software-support environments can still reveal weak signals about operational pain, unmet needs, adoption barriers, workflow friction, and dissatisfaction with existing tools.

What this project is not: it is not generic sentiment analysis, social listening, product hunting, financial advice, or an automated investment recommendation system. It is a decision-support workflow for organizing weak public signals so a human evaluator can ask better diligence questions.

## Current Scope

This MVP is currently scoped to early-stage app/software ventures that build AI-enabled tools for small-business operations, lean teams, and one-person companies.

The category includes:

- Workflow automation tools.
- Admin automation tools.
- Lightweight business operations software.
- AI-enabled productivity systems for small businesses.
- Embedded AI tools for solo operators and lean teams.
- Operational software that reduces manual work, setup burden, or tool fragmentation.

The memo is category-level evidence support, not a review of one specific app.

## Source Rationale

The MVP combines two public, practical weak-signal environments:

- **Source 1: Hacker News comments via Algolia API.** Hacker News is used as a category and industry weak-signal source. It is useful for early market conversation, problem articulation, unmet needs, user frustrations, and demand clues from a technical and startup-aware community.
- **Source 2: Stack Overflow public questions via Stack Exchange API.** Stack Overflow is used as an implementation-friction and adoption-barrier source. It is useful for setup friction, onboarding pain, integration problems, API confusion, practical workflow constraints, and dissatisfaction with current tools.

These sources are complementary. Hacker News helps surface market conversation and problem language; Stack Overflow helps surface practical adoption and implementation friction. Together, they support a lightweight venture-category memo without relying on private data, Reddit, or brittle scraping.

### Source Roles

Hacker News comments help answer:

- What problem language appears in public technical/startup discussion?
- Are people describing recurring workflow, admin, or operational pain?
- Are there early demand clues, comparisons, or dissatisfaction signals around a venture category?

Stack Overflow questions help answer:

- Where do users or developers hit setup, API, integration, credential, or onboarding friction?
- Which tools create practical adoption barriers?
- What implementation details might slow a small team or solo operator before they get product value?

The pipeline treats both sources as weak evidence. Hacker News is not a representative market survey, and Stack Overflow is not a customer-review database. Their value is in surfacing auditable public signals that can guide further human diligence.

## What the Pipeline Does

The pipeline:

1. Collects public text from Hacker News and Stack Overflow through bounded page-level API adapters.
2. Saves raw responses for debugging and auditability.
3. Cleans and normalizes text while preserving source links.
4. Filters out low-quality evidence such as job postings, promotional copy, launch announcements, and generic listings.
5. Scores and ranks evidence for relevance to small-business operations, lean-team workflows, setup burden, integration pain, manual work, and adoption friction.
6. Extracts weak-signal categories for a venture-evaluation support memo.
7. Exports CSV, Markdown, static HTML, and JSON artifacts.

## Outputs

Main outputs are written to:

- `output/csv/`: evidence tables, normalized items, section summaries, and excluded-item logs.
- `output/md/`: Markdown venture signal memo.
- `output/html/`: static HTML venture signal memo for portfolio review.
- `data/raw/`: raw source responses and collector diagnostics.
- `data/processed/`: normalized items, analysis JSON, quality-filter logs, and relevance-filter logs.
- `data/storage/`: local SQLite run index for run metadata, page-level collection state, resumable collection state, diagnostics, stage records, summaries, and evidence rows.

Fallback demo records are clearly labeled if a live endpoint is unavailable.

## Quick Start

Requires Python 3.10 or newer.

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python src/main.py
```

### macOS or Linux

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python src/main.py
```

After the run completes, open the newest files in:

- `output/md/`
- `output/html/`
- `output/csv/`

Markdown and HTML reports now include a cluster-first pain-point section before the older category evidence sections. CSV output also includes `<run_id>_evidence_clusters.csv` for dashboard-friendly cluster browsing.

The run is also indexed in `data/storage/pipeline_runs.sqlite3` for later run comparison and dashboard work.

The storage read layer currently exposes `list_runs`, `get_run_summary`, `get_collection_pages`, `get_collection_states`, `get_processing_batches`, `get_model_artifacts`, `get_embedding_artifacts`, `get_cluster_artifacts`, `get_run_chain_summary`, `get_run_chain_evidence_rows`, `get_run_chain_model_artifacts`, `get_run_chain_embedding_artifacts`, `get_run_chain_cluster_artifacts`, `get_resume_start_pages`, `get_resume_lineage_run_ids`, `get_raw_item_source_keys`, and `get_evidence_rows` from `src/storage/sqlite_store.py`.

Filtering and relevance preparation run in configurable batches. Each run writes `data/processed/<run_id>_batch_summary.json` and stores the same batch records in SQLite.

Model outputs are stored as model artifacts with artifact type, model name, model version, input hash, batch index, item ID, source ID, timestamp, and JSON payload. The current deterministic baseline writes `classification` artifacts through `heuristic-signal-classifier@v1`, lightweight `embedding` artifacts through `hashed-text-embedding@v1`, and embedding-assisted `evidence_cluster` artifacts through `heuristic-evidence-clusterer@v2`. Cluster artifacts group prepared evidence into interpretable pain-point themes such as integration reliability, setup friction, workflow automation failure, manual admin burden, and AI trust concerns. The same storage shape can later hold transformer embeddings, clustering labels, reranker outputs, and LLM summaries.

The NLP design is documented in `docs/nlp_methodology.md`.

## Inspect Stored Runs

Use the inspection CLI to review stored SQLite runs without opening the database directly:

```powershell
python src/inspect_runs.py --list --limit 5
python src/inspect_runs.py --run-id 20260525_211623
python src/inspect_runs.py --run-id 20260525_211623 --collection-state
python src/inspect_runs.py --run-id 20260525_211623 --batches
python src/inspect_runs.py --run-id 20260525_211623 --artifacts --artifact-type classification
python src/inspect_runs.py --run-id 20260525_211623 --embeddings
python src/inspect_runs.py --run-id 20260525_211623 --clusters
python src/inspect_runs.py --run-id 20260525_211623 --evidence --limit 10
python src/inspect_runs.py --run-id 20260525_211623 --chain
python src/inspect_runs.py --run-id 20260525_211623 --chain --evidence --limit 10
python src/inspect_runs.py --run-id 20260525_211623 --chain --artifacts --artifact-type classification
python src/inspect_runs.py --run-id 20260525_211623 --chain --embeddings
python src/inspect_runs.py --run-id 20260525_211623 --chain --clusters
```

`--collection-state` shows per-source/query pagination state. `--batches` shows processing batch records. `--artifacts` shows stored model artifacts and can be combined with `--artifact-type` or `--batch-index`. `--embeddings` shows text embedding artifacts. `--clusters` shows pain-point cluster artifacts with representative item IDs and product-opportunity hints. `--evidence` shows ranked evidence rows and can be combined with `--category`. `--chain` treats a resumed run and its parent chain as one aggregate view for summary counts, evidence, embeddings, clusters, and artifacts.

## Evaluate Clusters

Export a review file from an existing run:

```powershell
python src/export_cluster_review.py --run-id 20260525_232531
```

This writes:

- `output/csv/<run_id>_cluster_review.csv`
- `output/csv/<run_id>_cluster_review_labels.json`

Review the CSV, edit the JSON labels where needed, then evaluate clustering quality.

Use the cluster evaluation CLI to compare predicted clusters against reviewed `source_id` labels:

```powershell
python src/evaluate_clusters.py `
  --raw-items-file samples/small_business_operations_raw_items.json `
  --labels-file samples/cluster_review_labels.json `
  --embedding-backend hashing `
  --cluster-similarity-threshold 0.12
```

To compare multiple thresholds in one run:

```powershell
python src/evaluate_clusters.py `
  --raw-items-file samples/small_business_operations_raw_items.json `
  --labels-file samples/cluster_review_labels.json `
  --embedding-backend hashing `
  --cluster-similarity-thresholds "0.05;0.12;0.2" `
  --output-json output/csv/cluster_threshold_sweep_hashing.json `
  --output-csv output/csv/cluster_threshold_sweep_hashing.csv
```

To compare embedding backends after installing optional transformer dependencies:

```powershell
python src/evaluate_clusters.py `
  --raw-items-file samples/small_business_operations_raw_items.json `
  --labels-file samples/cluster_review_labels.json `
  --embedding-backends "hashing;sentence-transformer:sentence-transformers/all-MiniLM-L6-v2" `
  --cluster-similarity-thresholds "0.05;0.12;0.2" `
  --output-json output/csv/cluster_backend_comparison.json `
  --output-csv output/csv/cluster_backend_comparison.csv
```

The evaluator reports pairwise precision, recall, and F1. The sample label file is intentionally small; expand it with human-reviewed examples before using the metric to tune thresholds or embedding models.

To continue live collection from a previous run's unfinished page state:

```powershell
python src/main.py --resume-from-run-id 20260525_211623 --max-discussion-items 50 --max-review-items 50
```

Resume mode uses only unfinished source/query states from the previous run. It also skips raw items already seen in the parent resume chain using `source_name + source_id` and writes skipped records to `data/processed/<run_id>_cross_run_duplicate_items.json`. Offline `--raw-items-file` runs skip live collectors and do not create collection state.

An illustrative sample memo is available at `docs/sample_venture_signal_memo.md`.

## Custom Query Runs

You can run the pipeline with your own venture category and query families through command-line arguments:

```powershell
python src/main.py `
  --theme "AI tools for real estate agents" `
  --community-queries "real estate CRM pain;agent workflow automation" `
  --stackexchange-queries "crm webhook issue;real estate api integration" `
  --max-discussion-items 50 `
  --max-review-items 50 `
  --discussion-page-size 25 `
  --discussion-max-pages-per-query 2 `
  --discussion-sort date `
  --review-page-size 25 `
  --review-max-pages-per-query 2 `
  --review-sort activity `
  --review-order desc `
  --processing-batch-size 500
```

You can also save a reusable JSON run configuration:

```powershell
python src/main.py --config configs/example_run.json
```

For deterministic offline demos or regression checks, run from a local raw-items sample:

```powershell
python src/main.py --raw-items-file samples/small_business_operations_raw_items.json
```

CLI arguments take priority over JSON config files. JSON config files take priority over environment variables. Environment variables take priority over built-in defaults.

### Collection Controls

The live API collection policy is configurable per run:

- `--enable-discussion-source` / `--disable-discussion-source`: include or skip Hacker News.
- `--enable-review-source` / `--disable-review-source`: include or skip Stack Exchange.
- `--max-discussion-items` / `--max-review-items`: maximum retained items per source.
- `--discussion-page-size` / `--review-page-size`: requested API page size. Use `0` for automatic sizing.
- `--discussion-max-pages-per-query` / `--review-max-pages-per-query`: maximum pages requested for each query. Use `0` for automatic depth based on item limits.
- `--discussion-sort`: Hacker News Algolia order, either `relevance` or `date`.
- `--review-sort` and `--review-order`: Stack Exchange sort field and direction.
- `--request-timeout`: per-request HTTP timeout.

The selected collection policy is stored in run metadata, SQLite, and `inspect_runs.py` output so later dashboard or NLP results remain auditable.

### Embedding Controls

The default embedding backend is the lightweight deterministic hasher:

```powershell
python src/main.py --embedding-backend hashing
```

For stronger local semantic similarity, install the optional transformer dependency and choose a local sentence-transformer model:

```powershell
pip install -r requirements-transformer.txt
python src/main.py `
  --embedding-backend sentence-transformer `
  --embedding-model sentence-transformers/all-MiniLM-L6-v2
```

The embedding backend is stored in run metadata. Transformer mode is intended for local machines that can handle the model download and inference cost.

Use `--cluster-similarity-threshold` to tune how aggressively items are merged inside the same pain-mechanism bucket. Lower values merge more items; higher values split clusters more strictly.

## Running Tests

The baseline test suite uses Python's standard `unittest` module and does not require extra test dependencies.

```powershell
python -m unittest discover -s tests -v
```

## Optional Configuration

The default configuration is already set for the current MVP scope. You can also override it with environment variables:

```powershell
$env:PRODUCT_THEME="AI-enabled tools for small-business operations, lean teams, and one-person companies"
$env:COMMUNITY_QUERIES="small business workflow pain;admin automation frustration;CRM frustration small business;solo founder automation"
$env:STACKEXCHANGE_SITE="stackoverflow"
$env:STACKEXCHANGE_QUERIES="workflow automation integration;crm api integration problem;zapier automation error;n8n setup issue"
$env:MAX_DISCUSSION_ITEMS="50"
$env:MAX_REVIEW_ITEMS="50"
$env:EMBEDDING_BACKEND="hashing"
$env:CLUSTER_SIMILARITY_THRESHOLD="0.12"
python src/main.py
```

## Live Data Debugging

Each run prints:

- Source endpoints used.
- Query families used.
- Live item counts.
- Fallback status.
- Failure reasons, if any.
- Quality-filter counts.
- Relevance-filter counts.
- SQLite run-index path.

Debug files are saved by default:

- `data/raw/latest_source1_raw.json`
- `data/raw/latest_source2_raw.json`
- `data/raw/<run_id>_collector_diagnostics.json`

Set `DEBUG_SAVE_RAW=false` to disable latest-response debug files.

## Report Sections

The generated memo includes:

1. Project title and run metadata.
2. Data sources used.
3. Scope, venture category, and query family analyzed.
4. Volume of evidence analyzed.
5. Recurring operational pain signals.
6. Unmet needs.
7. Adoption barriers.
8. Dissatisfaction with current solutions.
9. Differentiation opportunities.
10. Community traction clues and demand clues.
11. Competing solution mentions.
12. Key uncertainty notes.
13. Implications for early-stage venture evaluation.
14. Limitations and why this does not replace human judgement.

## Limitations

This project is a supplementary weak-signal decision-support prototype, not an automated investment recommendation system. It does not output investment advice or invest/do-not-invest recommendations. It outputs auditable weak-signal evidence that still requires human judgement, source review, and broader diligence.

Important limitations:

- Public online evidence is noisy, incomplete, and selection-biased.
- Hacker News skews toward technical and startup-aware audiences.
- Stack Overflow skews toward implementation-facing technical problems.
- Heuristic relevance scoring is transparent but not a validated machine-learning model.
- Evidence snippets should be checked in source context before any consequential decision.
- A higher evidence count does not mean a venture category is attractive; it means the pipeline found more heuristic matches.

## Portfolio Framing

This project demonstrates AI-assisted decision-support thinking by transforming incomplete public signals into auditable, structured evidence. It is designed for early-stage venture and enterprise evaluation under uncertainty, where weak signals can inform diligence questions but should not replace human judgement.
