# Project Aegis API Configuration Handoff

Status: `V2.3-A handoff template`

Purpose: collect the non-secret metadata needed to connect approved external
research or market-data APIs to Project Aegis.

For candidate refresh APIs, also read:

- `docs/V2_8_I_REAL_USER_API_HANDOFF_REFRESH.md`
- `config/external_api_connectors.user-template.json`

## What To Provide

For each API, provide only:

- `connector_id`: stable lowercase ID, for example `api_user_research_approved_env`.
- `name`: human-readable provider name.
- `provider_type`: `official_regulator`, `official_company`,
  `licensed_market_data`, `user_provided_research_api`, or `social_official_api`.
- `markets`: one or more of `A`, `H`, `US`, `GLOBAL`.
- `base_url`: endpoint base URL without tokens, query secrets, cookies, or
  credentials.
- `auth_method`: usually `env_var` or `none`.
- `required_env_vars`: environment variable names only, for example
  `AEGIS_RESEARCH_API_KEY`.
- `license_status`: `approved`, `pending`, `not_required`, `forbidden`, or
  `unknown`.
- `retention_policy`: `metadata_only`, `summary_only`, `short_excerpt`, or
  `no_storage`.
- `allowed_purposes`: for example `strategy_research_ingestion`,
  `official_filings_context`, or `evidence_metadata`.
- `can_connect`: `true` only when the provider is approved and inside Aegis
  safety boundaries.
- `notes`: optional non-secret notes.

## What Not To Provide

Do not provide:

- API key values.
- Secret values.
- Cookies.
- Bearer tokens.
- OAuth refresh tokens.
- Passwords.
- Broker credentials.
- Trading webhook URLs.
- Any URL containing token, secret, api_key, password, bearer, or cookie
  material.

If an API requires a key, create the key locally as an environment variable and
share only the environment variable name with Aegis.

## Environment Variable Pattern

Use names like:

```text
AEGIS_RESEARCH_API_KEY
AEGIS_MARKET_DATA_API_KEY
AEGIS_SOCIAL_API_KEY
```

The actual values must stay outside the repo and Vault.

## Allowed API Types

Allowed after policy validation:

- Official regulator APIs.
- Official company APIs.
- Licensed market-data APIs with approved license.
- User-provided research APIs with approved license/terms.
- Social official APIs only after terms and retention rules are approved.

Denied:

- Broker APIs.
- Trading webhooks.
- Unknown-license paid data.
- Unauthorized scraping.
- Cookie/session-based access.
- API specs containing secret values.

## Flow After Handoff

1. User provides non-secret metadata only.
2. Aegis validates the connector spec.
3. Approved API dry-run fetch stores only summary, hash, status metadata, and
   env var names.
4. API research summaries become strategy update proposals.
5. Proposals must pass sandbox validation before strategy changes.
6. Suggestions remain simulation-only and require user manual execution outside
   Aegis.

## Current Example

See:

- `config/external_api_connectors.example.json`
- `config/external_api_connectors.user-template.json`

These files are safe to keep in repo because they contain env var names only
and no secret values.
