# Project State

## Current Project Objective

Build a lightweight, credible MVP of an AI-assisted community signal pipeline for early-stage venture-category evaluation.

The project now demonstrates how messy public discussion and public software feedback signals can be transformed into structured supplementary evidence for uncertainty-aware human decision-making. The current category scope is AI-enabled tools for small-business operations, lean teams, solo operators, and one-person companies.

## Current Repo Status

- Repository path: `C:\Users\1\Documents\AI-Assisted Community Signal Pipeline for Early-Stage Venture Evaluation`
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
- Live retrieval diagnostics that print endpoint, query, live item count, fallback status, failure reason, and final fallback count.
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

## Limitations Discovered So Far

- The extraction logic is heuristic and transparent, not a trained or validated NLP model.
- The text-quality filter is heuristic and may exclude some useful edge cases; its reason logs should be reviewed after live runs.
- The current fallback dataset is intentionally user-like, so it does not demonstrate many exclusions by itself; live runs or synthetic checks are better for inspecting exclusion behavior.
- Hacker News is biased toward technical audiences.
- Stack Overflow questions skew toward technical users and implementation-facing problems, so they should be interpreted as evidence of practical barriers rather than full market demand.
- Live public endpoints may fail due to connectivity, rate limits, or source-side changes, so fallback demo records are included.
- No formal benchmark or human evaluation workflow exists yet.
- No frontend framework exists; output is static HTML by design.

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

## Open Problems

- Add tests for collectors, processors, analyzers, and exporters.
- Add command-line arguments as a friendlier alternative to environment variables.
- Improve evidence clustering so repeated weak signals are grouped more semantically.
- Review excluded-item logs after live runs and tune filter rules where they are too strict or too permissive.
- Inspect relevance-filtered logs after live runs to confirm that pure technical debugging and generic enterprise complaints are being down-ranked without losing useful implementation-friction evidence.
- Add optional LLM-assisted summarization while preserving evidence snippets.
- Create a curated deterministic sample dataset for portfolio demos.
- Define a small human evaluation rubric for usefulness and traceability.
- When running outside the sandbox with internet access, confirm that the live Hacker News and Stack Exchange endpoints return fresh public records.
- If live endpoints succeed, update this file with the run ID, item counts, and any source-specific issues discovered.

## Next Recommended Actions

1. Run `python src/main.py` to generate the first local demo outputs.
2. Inspect the Markdown and HTML reports in `output/md/` and `output/html/`.
3. Commit the MVP once outputs are verified.
4. Add tests for the text cleaning, signal extraction, and exporter modules.
5. Add a small deterministic sample dataset for repeatable portfolio screenshots.
6. Consider optional LLM-assisted summarization after the heuristic baseline is stable.
7. Update `PROJECT_STATE.md` after each substantive decision or implementation step.

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
