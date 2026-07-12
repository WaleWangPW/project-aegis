# P23.2 Signal Snapshots — Invalid Previous Implementation

The previous P23.2 implementation is quarantined and must not be used.

Confirmed defects:

- Randomly generated stock symbols
- Simulated natural-calendar dates
- Non-trading dates
- Only three snapshots
- Missing entry and exit dates
- Placeholder source hashes
- Validator safety checks hard-coded to pass
- No independent trade-calendar audit

P23.3 must remain blocked until a real-data P23.2 rebuild passes independent validation.
