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

## What the Pipeline Does

The pipeline:

1. Collects public text from Hacker News and Stack Overflow.
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

## Optional Configuration

The default configuration is already set for the current MVP scope. You can override it with environment variables:

```powershell
$env:PRODUCT_THEME="AI-enabled tools for small-business operations, lean teams, and one-person companies"
$env:COMMUNITY_QUERIES="small business workflow pain;admin automation frustration;CRM frustration small business;solo founder automation"
$env:STACKEXCHANGE_SITE="stackoverflow"
$env:STACKEXCHANGE_QUERIES="workflow automation integration;crm api integration problem;zapier automation error;n8n setup issue"
$env:MAX_DISCUSSION_ITEMS="50"
$env:MAX_REVIEW_ITEMS="50"
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
