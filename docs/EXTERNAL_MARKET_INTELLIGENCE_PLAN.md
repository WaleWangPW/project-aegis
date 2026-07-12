# Project Aegis External Market Intelligence Plan

Status: `proposed`

Purpose: design how Aegis may later use online market information for stock
research without breaking evidence, copyright, privacy, or trading boundaries.

## Goal

Allow Project Aegis to collect and summarize external stock-related information
such as financial news, company filings, Reddit discussions, X posts, and public
comments from relevant market figures.

This must support research and decision review only. It must not become an
automatic trading signal engine.

## Source Classes

### Licensed Financial Data

Examples:

- Bloomberg data products or APIs.
- Other paid or licensed financial-data providers.

Rules:

- Use only with an approved license or API access.
- Do not scrape paywalled pages.
- Do not store full copyrighted articles.
- Store metadata, short summaries, source IDs, timestamps, and links.
- Treat the provider's license terms as a hard boundary.

### Public Web and Company Sources

Examples:

- Company investor relations pages.
- SEC/Exchange filings.
- Press releases.
- Official earnings call transcripts where allowed.

Rules:

- Prefer official company or regulator sources.
- Store source URL, retrieval time, title, and concise summary.
- Do not treat a summary as verified unless the source itself is verified.

### Social Sources

Examples:

- Reddit posts and comments.
- X/Twitter posts.
- Public statements from named executives, analysts, investors, or regulators.

Rules:

- Prefer official APIs and terms-compliant access.
- Store post ID, author handle, URL, timestamp, text excerpt within allowed
  limits, and source status.
- Do not treat social sentiment as fact.
- Public-figure posts are evidence of "this person said X", not evidence that
  X is true.
- Avoid doxxing, private accounts, deleted content, or credentials.

## Evidence Levels

| Level | Meaning | Accepted For Decision Support |
|---|---|---:|
| `verified_primary` | Company/regulator/source-owned record | Yes |
| `licensed_provider` | Licensed vendor data within usage rights | Yes |
| `verified_social_statement` | Public post from verified or known source | Limited |
| `community_discussion` | Reddit/X/forum discussion | Context only |
| `llm_summary` | LLM generated summary | No, unless linked to accepted evidence |
| `unverified_web` | Unknown source or unverifiable scrape | No |

## Required Record Shape

Every external item must include:

- `source_id`
- `source_type`
- `symbol`
- `market`
- `retrieved_at`
- `published_at`
- `author_or_publisher`
- `url_or_external_id`
- `license_status`
- `evidence_level`
- `summary`
- `quoted_excerpt`
- `hash`
- `retention_policy`

## Forbidden

- Scraping Bloomberg or other paywalled sites without license.
- Storing full copyrighted articles.
- Bypassing login, paywall, robots, API limits, or terms.
- Reading or storing cookies, broker credentials, API secrets, or recovery codes.
- Treating Reddit/X sentiment as verified fact.
- Letting online posts directly trigger Action/Exit.
- Auto-trading, broker API, webhook trading, or strategy mutation.

## Recommended Implementation Order

1. `V2.0-D`: local Event Timeline and Scenario records from controlled inputs.
2. `V2.0-E`: External Source Registry and Source Policy Gate.
3. `V2.0-F`: official/company/regulator source fetcher.
4. `V2.0-G`: Reddit/X API-backed social monitor, only after API access and
   rate/retention rules are approved.
5. `V2.0-H`: licensed provider adapter, only after user confirms license.

## Current Decision

Do not implement live web ingestion yet. First implement event and scenario
records that can later accept external evidence safely.

