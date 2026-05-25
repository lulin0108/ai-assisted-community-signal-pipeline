# Decision Log

## 2026-05-25: Build in the Existing Repository

Decision: adapt the current repository instead of creating a new one beside it.

Rationale: the repo already contains the intended memory foundation files and no conflicting implementation. Building in place keeps `AGENT.md` and `PROJECT_STATE.md` as the project memory source of truth.

## 2026-05-25: Use Hacker News Comments as Source Type 1

Decision: use Hacker News comments through the public Algolia API for discussion/community data.

Rationale:

- No Reddit dependency.
- No authentication required.
- Public JSON endpoint.
- Relevant for problem discussion, technical adoption pain, workflow frustrations, and community demand articulation.
- Practical for a fast, reproducible demo.

Tradeoff: Hacker News is biased toward technical audiences and should not be treated as representative of the full market.

## 2026-05-25: Replaced Apple App Store Reviews with GitHub Public Issue Comments as Source Type 2

Decision: use GitHub public issue comments from public repositories for review/feedback-style data.

Rationale:

- Developer-friendly public REST API.
- Structured JSON responses.
- Better fit for early-stage app ventures, AI software, and digital productivity tools.
- Public issue comments often contain setup pain, onboarding friction, integration problems, feature requests, and product dissatisfaction.
- More suitable than Apple customer review retrieval for a lightweight public-source portfolio pipeline.

Tradeoff: GitHub evidence skews toward technical users, developer tools, open-source communities, and implementation-facing feedback.

## 2026-05-25: Use Heuristic NLP for the MVP

Decision: use lightweight keyword and pattern heuristics instead of heavy ML training.

Rationale: the MVP should be beginner-friendly, runnable, auditable, and focused on the end-to-end decision-support workflow. The architecture leaves room for later LLM-assisted summarization or classifier upgrades.

## 2026-05-25: Avoid Investment Scores

Decision: generate a structured support memo rather than an invest/do-not-invest score.

Rationale: this preserves the project framing as supplementary venture-evaluation evidence under uncertainty, not automated investment recommendation.

## 2026-05-25: Add Source-Aware Text Quality Filtering

Decision: add a pre-analysis filter that favors user-generated or user-facing evidence over company self-description.

Rationale: the project is about structuring weak public signals into auditable decision-support evidence. Job postings, career pages, landing-page copy, promotional summaries, and directory snippets weaken the signal quality because they are not user discussion or customer feedback.

The filter now records raw item counts, filtered-out counts, retained evidence candidates, source-level counts, and exclusion reasons.

## 2026-05-25: Reframed Scope Around AI-Enabled Small-Business Operations Tools

Decision: move away from a narrow meeting-notes or single-app framing and use a venture-category query family.

Rationale: for PhD application portfolio value, the project should demonstrate uncertainty-aware decision support for evaluating a category of early-stage ventures, not a narrow product review workflow.

Default query family:

- Operational pain: `small business workflow pain`
- Adoption barrier: `admin automation frustration`
- Dissatisfaction with current solutions: `CRM frustration small business`
- One-person company / lean-team angle: `solo founder automation`

GitHub feedback query family:

- `setup`
- `integration`
- `onboarding`
- `feature request`

## 2026-05-25: Simplified GitHub Source 2 Retrieval

Decision: replace GitHub search-based retrieval with direct recent-issue retrieval from a fixed public repository, followed by issue-comment retrieval.

Rationale: direct repository endpoints are simpler and more reliable than search endpoints for a lightweight public-source portfolio demo. The implementation now uses `requests.Session()`, explicit GitHub headers, longer timeout, and retries with short backoff.

Default repository: `n8n-io/n8n`, because it is a public workflow automation project aligned with small-business operations and automation tooling.

## 2026-05-25: Replaced GitHub Source 2 with Stack Overflow

Decision: stop using GitHub as Source 2 and use Stack Exchange / Stack Overflow public questions instead.

Rationale: local testing showed GitHub Source 2 remained unreliable, with zero live issues/comments and read timeouts. Stack Overflow is a better live public source for implementation barriers because users ask concrete questions about setup, integrations, workflow automation errors, API confusion, and operational software constraints.

Default Stack Exchange query family:

- `workflow automation integration`
- `crm api integration problem`
- `zapier automation error`
- `n8n setup issue`

## 2026-05-25: Added Evidence Relevance Scoring and Section Ranking

Decision: add a lightweight relevance scorer before analysis and rank section evidence by section-specific relevance.

Rationale: live public data can include noisy, generic, promotional, or weakly related text. The project should prioritize evidence that clearly relates to small-business operations, workflow friction, admin burden, setup/onboarding pain, integration problems, operational software complexity, and lean-team or solo-operator constraints.

The scorer down-ranks or excludes founder self-promotion, link drops, generic enterprise complaints with weak scope fit, and off-topic quotation-like text.
