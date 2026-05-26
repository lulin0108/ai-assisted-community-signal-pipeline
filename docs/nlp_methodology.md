# NLP Methodology

This document explains the current NLP layer for the AI-Assisted Community Signal Pipeline.

## Purpose

The NLP layer turns noisy public text into auditable evidence groups. It is designed to support human diligence, not to predict investment outcomes.

The current NLP layer answers:

- Which public records look like useful evidence?
- Which records are relevant to the venture category?
- What type of weak signal does each record contain?
- Which records describe similar pain points?
- Which evidence examples should represent each pain-point group?

## Current Pipeline

The current text-processing path is:

```text
raw_items
-> quality filtering
-> relevance preparation
-> classification artifacts
-> embedding artifacts
-> evidence cluster artifacts
-> cluster-first report / inspect CLI / SQLite
```

## Quality Filtering

The quality filter removes records that are unlikely to be useful customer or operator evidence.

It down-selects away from:

- Job posts.
- Promotional copy.
- Launch-style announcements.
- Generic listings.
- Weakly relevant technical text.

The output is a smaller set of evidence candidates with quality reasons preserved.

## Relevance Preparation

Relevance preparation scores each retained record against the current venture category. It favors evidence about small-business operations, workflow friction, setup pain, integration problems, manual work, admin burden, adoption barriers, and lean-team constraints.

This stage produces `prepared_items`, which are the main input for downstream NLP artifacts.

## Classification Artifacts

Each prepared item receives a deterministic `classification` artifact from `heuristic-signal-classifier@v1`.

The classifier assigns labels such as:

- `business_scope`
- `workflow_friction`
- `practical_tooling`
- `adoption_barrier`
- `dissatisfaction`
- `ai_operational`
- `implementation_feedback`

These labels make item-level evidence easier to inspect and later filter in a dashboard.

## Embedding Artifacts

Each prepared item receives an `embedding` artifact through the configured embedding provider.

The default provider is `hashed-text-embedding@v1`, a deterministic hashed text vector:

- Text fields are tokenized from title, cleaned text, relevance reasons, and quality reasons.
- Tokens are mapped into a fixed 64-dimensional vector using a stable hash.
- The vector is L2-normalized.
- Sparse values are stored as nonzero indices and values.

This default is not a transformer embedding. It is a lightweight local baseline that keeps the default install small.

The optional provider is `sentence-transformer-embedding@v1`, enabled with `--embedding-backend sentence-transformer`. It uses `sentence-transformers` locally and stores dense vector values in the same artifact layer. The default model identifier is `sentence-transformers/all-MiniLM-L6-v2`, and users can override it with `--embedding-model`.

The key benefit is architectural: embeddings are now first-class artifacts in JSON and SQLite, so the vector producer can change without rewriting storage, clustering, reports, or the inspection CLI.

## Evidence Cluster Artifacts

Prepared items are grouped into `evidence_cluster` artifacts from `heuristic-evidence-clusterer@v2`.

Clustering uses two layers:

1. Pain-mechanism candidate buckets.
2. Configured embedding cosine similarity inside each bucket.

The first layer prevents unrelated issues from merging just because they share generic vocabulary. For example, pricing complaints and CRM sync failures should not be merged.

The second layer uses vector similarity to group items that are textually or semantically close within the same pain mechanism. In hashing mode this is mostly lexical similarity. In transformer mode it can capture more paraphrase-level similarity, depending on the local model.

Current pain-mechanism buckets include:

- Customer data sync and integration reliability.
- Workflow automation reliability and troubleshooting.
- Setup, onboarding, and credential configuration.
- Admin fragmentation and manual follow-up burden.
- Lean-team adoption and maintenance burden.
- AI trust, accuracy, and operational reliability.
- Product complexity and switching-cost friction.
- General operational-tool signal.

Each cluster stores:

- `cluster_id`
- `cluster_key`
- readable label
- product-opportunity hint
- item count
- member item IDs
- member source IDs
- representative item IDs
- representative source IDs
- source mix
- average and max relevance score
- top terms
- evidence excerpts
- similarity-to-representative scores
- embedding model metadata
- grouping basis and similarity threshold

## Why This Structure

The design is intentionally layered:

- Rules and filters remove obvious noise cheaply.
- Relevance scoring narrows attention to category-specific evidence.
- Embeddings create reusable text representations.
- Clusters reduce thousands of records into reviewable pain-point groups.
- Reports and dashboards can show clusters first, then let users drill into source evidence.

This avoids using an LLM to read every raw text record. Heavy models should operate on selected evidence, clusters, or representative examples.

## Report Shape

Markdown and HTML exports now surface pain-point clusters before the older category evidence sections. This makes larger runs easier to review because a human can first compare repeated pain mechanisms, source mix, representative item IDs, and product-opportunity hints, then inspect the underlying evidence.

CSV export includes a separate evidence-cluster table for later dashboard filtering and run comparison.

## Cluster Evaluation

`src/export_cluster_review.py` exports a human-review CSV and label-template JSON from an existing run's cluster artifacts and normalized items. Reviewers can inspect source IDs, titles, URLs, cluster assignments, top terms, and text excerpts, then edit the label JSON.

`src/evaluate_clusters.py` compares predicted clusters against a reviewed label file keyed by `source_id`. The current sample labels live at `samples/cluster_review_labels.json`.

The evaluator reports pairwise precision, recall, and F1:

- Precision asks whether predicted same-cluster pairs are also same-label pairs.
- Recall asks whether same-label pairs were recovered by the predicted clusters.
- F1 balances precision and recall.

This is the tuning path for `--cluster-similarity-threshold` and future transformer-backed clustering. The current sample is intentionally small and should be expanded with reviewed real examples before treating scores as meaningful quality estimates.

The evaluator can also compare multiple thresholds in one run with `--cluster-similarity-thresholds`, which is the preferred path once there are enough reviewed labels to make threshold tuning meaningful. Use `--output-csv` to write one row per threshold for spreadsheet review or dashboard ingestion.

Use `--embedding-backends` to compare embedding providers in the same evaluation run. Backend specs are semicolon-separated; transformer specs can include a model identifier after a colon.

## Current Limitations

The default embedding is lexical. It can group related vocabulary, but it does not fully capture paraphrases or deeper semantic equivalence.

Transformer mode requires local installation of `sentence-transformers` and may download model weights. It is better suited to local machines than lightweight hosted environments.

The current cluster labels and product-opportunity hints are deterministic templates. They are useful for inspection, but they are not learned topics.

The current similarity threshold is a baseline parameter. It should be tuned against human-reviewed examples as the sample set grows.

## Future Upgrade Path

The next NLP upgrades should preserve the same artifact interface while replacing internals:

1. Tune the local sentence-transformer option against a reviewed sample.
2. Add clustering such as agglomerative clustering or HDBSCAN.
3. Store cluster quality diagnostics.
4. Add human feedback labels for useful/noisy/duplicate/misclassified clusters.
5. Optionally use an LLM to summarize clusters with source-linked citations.

The LLM should summarize organized evidence, not act as the primary compute layer over unbounded raw text.
