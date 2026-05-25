# Roadmap

## MVP Complete

- Combine one public discussion source and one public Stack Overflow implementation-feedback source.
- Preserve source provenance through the pipeline.
- Filter low-quality source text before analysis.
- Extract recurring operational pain, unmet needs, adoption barriers, dissatisfaction with current tools, differentiation opportunities, demand clues, and competitor mentions.
- Export CSV, Markdown, and static HTML reports.
- Keep the implementation modular and beginner-friendly.
- Frame the MVP as category-level weak-signal evidence for AI-enabled small-business operations tools, not a single-product review.

## Near-Term Improvements

- Add a small test suite for collectors, processors, and exporters.
- Add a curated sample dataset for deterministic portfolio demos.
- Add optional LLM-assisted summarization while preserving evidence snippets and uncertainty notes.
- Improve duplicate detection and evidence clustering.
- Add command-line arguments for theme, source limits, and output directories.
- Tune the Stack Overflow query family against live public implementation-friction data from workflow automation, CRM/API integration, and operational-tool users.

## Later Research Directions

- Compare weak-signal extraction across multiple public communities.
- Add sector-specific signal dictionaries.
- Track uncertainty sources more formally.
- Evaluate whether extracted signals help human reviewers prioritize diligence questions.
- Add richer provenance metadata and reproducibility reports.
