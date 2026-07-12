# V2.10-B Real API Metadata Intake

- status: `PASS`
- intake_status: `blocked_missing_metadata`
- connector_id: `api_user_candidate_refresh_approved_env`
- blocked_by: `missing_connector_metadata`
- required_env_vars: `[]`
- present_env_vars: `[]`
- missing_env_vars: `[]`

## What This Means

- Create `config/external_api_connectors.local.json` from `config/external_api_connectors.user-template.json` and fill non-secret metadata only.

## Boundary

- Metadata preflight only.
- No network fetch.
- No raw config copy stored.
- Env var names only; env values are never serialized.
- No broker API, trading webhook, order placement, or production record mutation.
