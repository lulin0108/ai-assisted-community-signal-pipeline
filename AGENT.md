# AI-Assisted Community Signal Pipeline for Early-Stage Venture Evaluation

## Project Purpose

This project builds an AI-assisted pipeline for evaluating early-stage venture-category signals from community-visible discussion data and public review or feedback-style software data.

The system should help identify, organize, and interpret messy public online signals that may be relevant to early venture evaluation. It is currently scoped to early-stage ventures building AI-enabled tools for small-business operations, lean teams, solo operators, and one-person companies.

The current scope includes workflow automation tools, admin automation tools, lightweight business operations tools, AI-enabled small-business productivity systems, embedded AI tools for solo operators or lean teams, and operational software for small teams.

## Core Framing and Positioning

This project is a decision-support system, not an investment oracle.

It should produce evidence-grounded analysis that helps a human evaluator understand why a company, project, founder, product, or market signal may be worth further investigation. It should make uncertainty visible, preserve source context, and avoid presenting weak signals as conclusions.

The pipeline should be framed around:

- Community-visible evidence.
- Public implementation-feedback evidence from software users and operators.
- Transparent signal extraction.
- Source-linked findings.
- Explicit confidence and limitation notes.
- Reproducible intermediate artifacts where practical.
- Human review before any consequential decision.

## What This Project Is Not

This project is not:

- Financial, investment, legal, or tax advice.
- A replacement for professional diligence.
- A system for making automated investment decisions.
- A private-data scraping system.
- A Reddit-dependent pipeline.
- A credential-bypass or access-control circumvention tool.
- A personal surveillance or identity-enrichment system.
- A social-score shortcut that ranks people or companies without explainable evidence.
- A real-time trading, market-timing, or portfolio-management system.
- An exhaustive market-intelligence platform.
- A company self-description, career-page, or marketing-copy summarizer.
- A narrow single-product review tool for meeting notes or meeting summaries.

## Required Data-Source Boundaries

All data sources must be legally and ethically accessible.

Allowed source characteristics:

- Publicly accessible or clearly community-visible.
- Practical enough to support a working local demo.
- Available without bypassing authentication, rate limits, terms, robots restrictions, or access controls.
- Suitable for research and analysis with source attribution.
- Collectable without private personal data enrichment.

Required MVP source types:

- Source Type 1: public discussion or community data used for problem signals, unmet needs, user frustrations, and community demand articulation.
- Source Type 2: Stack Exchange / Stack Overflow public questions, used for setup friction, onboarding pain, integration problems, implementation barriers, dissatisfaction with current tools, and practical constraints faced by users of operational software.

Required query strategy:

- Use a venture-category query family, not a single fixed product query.
- Cover operational pain, adoption barriers, dissatisfaction with current solutions, and solo-operator or lean-team workflows.
- Default community query themes should include small-business workflow pain, admin automation frustration, CRM frustration for small business, and solo founder automation.
- Default Stack Exchange feedback themes should include workflow automation integration, CRM API integration problems, Zapier automation errors, and n8n setup issues.

Required evidence-quality boundary:

- Prioritize user-generated or user-facing evidence such as reviews, complaints, discussion comments, first-person experience statements, comparisons, and frustration language.
- Filter likely job postings, career pages, product landing-page copy, company self-description, promotional snippets, and generic directory/listing summaries before analysis.
- Prefer evidence quality over evidence quantity.

Disallowed source characteristics:

- Reddit as a project data source, because prior access reliability was not acceptable for this MVP.
- Private groups, private communities, private chats, private repositories, or private profiles unless explicit authorization is provided and documented.
- Paywalled scraping or unauthorized extraction from restricted services.
- Credential sharing, session hijacking, hidden API abuse, or access-control bypassing.
- Collection intended to infer sensitive personal attributes.
- Unlawful, deceptive, or terms-violating acquisition.

When a source is ambiguous, treat it as out of scope until there is an explicit documented reason to include it.

## Required Output Formats

Project outputs should be structured, auditable, and source-linked.

Expected output types include:

- Structured venture signal reports.
- Source-linked evidence summaries.
- Confidence and limitation notes.
- Extracted signal tables or JSON-like records.
- CSV outputs for normalized evidence and summary sections.
- Markdown outputs for readable review and handoff.
- Static HTML reports for portfolio-ready demo use.
- Reproducible intermediate artifacts where practical.
- Clear separation between observed evidence, inferred interpretation, and recommendation.
- Filtering logs that report raw item counts, excluded item counts, retained evidence candidates, and exclusion reasons.
- Evidence relevance scores and section-specific ranking so the strongest, most scope-aligned evidence appears first.

Outputs must not present speculation as fact. Any score, ranking, or recommendation must be accompanied by the evidence and assumptions used to produce it.

## Architectural Constraints

The architecture should remain modular and provenance-preserving.

Required pipeline boundaries:

- Ingestion: collect permitted source material.
- Normalization: standardize and clean source material without losing provenance.
- Signal extraction: identify relevant community, product, founder, market, or adoption signals.
- Scoring or prioritization: convert signals into explainable decision-support outputs.
- Report generation: produce structured, source-linked outputs for human review.

Architectural rules:

- Preserve source provenance through every stage.
- Prefer explicit configuration over hidden behavior.
- Keep transformations deterministic where practical.
- Keep raw evidence, normalized data, extracted signals, and generated reports conceptually distinct.
- Avoid tightly coupling data-source adapters to scoring or reporting logic.
- Design for repeatability and incremental extension.

## Coding Style Expectations

Future implementation should favor clarity and maintainability over cleverness.

Expected style:

- Use clear names and small, focused modules.
- Prefer typed interfaces or schemas where practical.
- Keep side effects explicit.
- Make data transformations easy to inspect and test.
- Use structured parsers and APIs instead of brittle string manipulation when practical.
- Keep configuration explicit and documented.
- Avoid unnecessary abstractions before the pipeline shape is validated.
- Add comments only where they clarify non-obvious decisions.
- Do not add defensive programming by default. Validate inputs and handle errors where the pipeline boundary requires it, but avoid broad guards, redundant checks, or fallback branches that hide real bugs.
- Keep comments minimal and functional. Do not add AI-like explanatory narration, restatements of obvious code, or long comments that do not add operational meaning.
- Write code in a normal engineering style: clear names, direct control flow, focused functions, and no decorative or over-explanatory scaffolding.

## Development Boundaries for the Next Phase

Future work should improve the current baseline without changing the project's responsible decision-support framing.

Important development boundaries:

- Treat the current system as a transparent baseline: public API collection, cleaning, quality filtering, heuristic relevance scoring, signal extraction, and report generation.
- Do not describe the current implementation as a trained machine-learning system or predictive model.
- If NLP or ML is added, use it to improve evidence quality, semantic grouping, labeling, summarization, uncertainty estimation, or reviewer workflow support.
- Do not add an investment-return predictor, invest/do-not-invest classifier, automated investment score, or financial recommendation layer.
- Keep user-supplied query support explicit and auditable. Store the venture category, query families, source limits, and run configuration with each run.
- Preserve the distinction between observed evidence, heuristic/ML interpretation, and human-facing implications.
- Keep deterministic heuristic outputs available even if LLM-assisted summarization is added later.
- Prefer API-based collection and documented source adapters over scraping web pages.
- Add new data sources only after documenting why the source is public, allowed, relevant, and provenance-preserving.
- Do not add private-data enrichment, profile enrichment, identity inference, or sensitive-attribute inference.
- Treat frontend or dashboard work as an evidence-review interface, not a trading, ranking, or automated decision product.
- If a database is introduced, preserve raw items, normalized items, analysis outputs, diagnostics, and run metadata as separate concepts.
- Future dashboards should allow filtering, source review, run comparison, and evidence inspection before adding higher-level recommendations.
- Large-scale collection must use explicit source limits, pagination, durable storage, deduplication, and batch processing. Do not turn the local script into an unbounded in-memory crawler.

## Current Technical Hardening Priorities

The current MVP is runnable and modular, but still prototype-grade. Future implementation should prioritize:

- Add tests for text cleaning, quality filtering, relevance scoring, signal extraction, collectors, and exporters.
- Define typed schemas for raw items, prepared items, evidence rows, diagnostics, and analysis results.
- Replace broad exception handling with narrower network, HTTP, parsing, validation, and programming-error paths.
- Add retry behavior consistently across collectors.
- Replace ad hoc `print` statements with structured logging that includes `run_id` and source context.
- Add command-line arguments or config-file support before building a UI around custom user queries.
- Create a deterministic sample dataset for repeatable demos and regression tests.
- Add a small evaluation rubric or labeled set to measure filtering precision, relevance ranking quality, and report usefulness.
- Add local storage and run indexing before attempting large-scale collection, dashboard-scale browsing, or semantic clustering across many runs.

## Documentation Expectations

Documentation is part of the system, not a side task.

Required documentation behavior:

- Read `AGENT.md` and `PROJECT_STATE.md` before substantive work.
- Treat `AGENT.md` as the stable source of truth for boundaries and operating rules.
- Treat `PROJECT_STATE.md` as the evolving source of truth for current progress and discoveries.
- Treat `docs/development_log.md` as the chronological record of completed development steps and verification.
- Update `PROJECT_STATE.md` after substantive implementation, data-source evaluation, design decisions, failed attempts, or important findings.
- Update `docs/development_log.md` after each completed development step with what changed, why it changed, verification, and the next likely step.
- Update `AGENT.md` only when project boundaries, constraints, or operating rules intentionally change.
- Record decisions in a way that future AI or coding assistants can understand without prior conversation context.

## Evaluation Criteria for Success

The project should be evaluated by whether it produces useful, traceable, and responsible venture-screening support.

Success criteria:

- Evidence is source-linked and auditable.
- Outputs distinguish facts, inferences, assumptions, and recommendations.
- Signals are useful for prioritizing further human diligence.
- The system handles noisy community data without overstating confidence.
- Results are reproducible enough to inspect and improve.
- Data-source boundaries are respected.
- The implementation remains modular and extensible.
- Future assistants can understand current state from `AGENT.md` and `PROJECT_STATE.md`.

## Non-Goals

This project does not aim to:

- Provide financial advice.
- Automate investment decisions.
- Predict returns with certainty.
- Replace human diligence.
- Build a private surveillance system.
- Scrape restricted or private data.
- Build a real-time trading or portfolio-management product.
- Produce exhaustive market intelligence across all companies and sectors.
- Optimize for virality, hype, or popularity without evidence quality.

## Do Not Change Without Explicit Reason

The following project rules should not be casually changed:

- `AGENT.md` is the stable boundary and operating-contract document.
- `PROJECT_STATE.md` is the evolving current-state and handoff document.
- `docs/development_plan.md` records the current implementation roadmap and should be updated when priorities or sequencing change.
- `docs/development_log.md` records completed work and verification history.
- `docs/scale_strategy.md` records the current plan for larger-scale public data collection, storage, batching, and analysis.
- The project must remain a decision-support system, not an investment oracle.
- The project must not provide financial, investment, legal, or tax advice.
- Data collection must remain limited to legally and ethically accessible public or community-visible sources.
- Provenance and source linkage must be preserved through the pipeline.
- Outputs must distinguish observed evidence from inferred interpretation.
- Scores or recommendations must be explainable and evidence-backed.
- Reports must not say "invest" or "do not invest."
- The architecture must remain modular across ingestion, normalization, signal extraction, scoring, and reporting.
- The MVP must combine both a public discussion source and a public review or feedback source.
- Source Type 2 should use Stack Exchange / Stack Overflow public API data unless explicitly changed for a documented reason.
- Reddit must not be introduced as a project data source.
- Future implementation should not introduce private-data enrichment, access-control bypassing, or opaque automated decision-making.
- Future implementation should not treat company marketing, job listings, or directory snippets as venture-evaluation evidence unless explicitly justified.
- Future implementation should not rank generic enterprise complaints, founder self-promotion, launch announcements, link drops, or off-topic quotations above concrete operational-tool evidence.
- Highly technical implementation details should be down-ranked unless they clearly show business-tool adoption burden, workflow friction, setup pain, or operational constraints for small businesses, lean teams, or solo operators.
- Future implementation should not recenter the project around one narrow product such as a meeting-note app without an explicit documented reason.
