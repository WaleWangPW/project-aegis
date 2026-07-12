# V2.8-I Real User API Handoff Refresh

Status: `handoff template`

Purpose: define the non-secret metadata needed to replace approved fixture
candidate refresh inputs with a user-provided API-backed candidate refresh.

This file is not an API key store, not a broker integration, and not a live
trading bridge.

## Current Boundary

- Current concrete candidates are from `approved_fixture_not_live_market_data`.
- Real user API candidate refresh remains blocked until local non-secret
  metadata and required local environment variables exist.
- API-backed candidates are research inputs only.
- API-backed candidates must still pass historical sandbox, Suggestion Gate,
  and simulation-only brief gates before user use.
- Aegis never places orders. The user executes manually outside Aegis and may
  feed screenshots or typed notes back as evidence.

## User Metadata To Provide

Create a local file:

```text
config/external_api_connectors.local.json
```

Use `config/external_api_connectors.user-template.json` as the template.

Provide only:

- `connector_id`
- `name`
- `provider_type`
- `markets`
- `base_url`
- `auth_method`
- `required_env_vars`
- `license_status`
- `retention_policy`
- `allowed_purposes`
- `can_connect`
- `endpoint_path`
- `request_query_template`
- `candidate_payload_schema`
- `rate_limit_note`
- `notes`

For candidate refresh, `candidate_payload_schema` must describe:

- `items_path`
- `symbol_field`
- `market_field`
- `name_field`
- `score_field`
- `status_field`
- `allowed_markets`
- `max_items_per_market`
- `freshness_policy`
- `candidate_summary_only`

## What Must Stay Local

Never put these in repo, Vault, docs, screenshots, or chat:

- API key values
- Secret values
- Cookies
- Bearer tokens
- OAuth refresh tokens
- Passwords
- Broker credentials
- Trading webhook URLs
- Query URLs containing token, secret, api_key, password, bearer, or cookie

If the API requires authentication, store the real value only in a local
environment variable. Aegis stores the variable name only, for example:

```text
AEGIS_CANDIDATE_REFRESH_API_KEY
```

## Required API Payload Shape

The API response may vary, but Aegis needs a summary-only candidate list that
can be mapped to:

```json
{
  "items": [
    {
      "symbol": "MSFT",
      "market": "US",
      "name": "Microsoft",
      "score": 0.78,
      "status": "Watch"
    }
  ]
}
```

Raw response bytes, request headers, cookies, and secret values must not be
stored. Aegis stores only summary fields, hashes, status metadata, and evidence
paths.

## Forbidden

- Real trading
- Broker API
- Trading webhook
- Automatic order placement
- Secrets in files
- Cookie/session access
- Unauthorized scraping or paywall bypass
- Strategy auto-mutation from API results
- Direct production `RecommendationRecord` mutation from API results

## Next Flow

1. User fills local non-secret metadata.
2. User exports required env vars locally.
3. Aegis runs metadata activation preflight.
4. Aegis runs bounded live API dry-run if preflight is ready.
5. Aegis stores summary/hash evidence only.
6. Candidate refresh output goes through sandbox and Suggestion Gate.
7. Any usable output remains simulation-only and manually executed by the user
   outside Aegis.
