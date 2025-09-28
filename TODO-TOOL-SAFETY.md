# TODO: Browser Tool Safety Hardening

## Response Caps
- [x] Enforce default byte caps per tool (`browser_get_text`, `browser_execute`, `browser_evaluate`) and document maximums.
- [x] Include truncation metadata in responses (boolean plus `returned_bytes` and `total_bytes_estimate`).

## Chunked Retrieval
- [x] Provide stateless chunk endpoints that accept byte offsets and return checksum of the source snapshot to detect drift.
- [x] Reject tampered or inconsistent offsets before issuing large upstream fetches.

## Configuration & Guardrails
- [x] Keep tool-specific limits configurable but enforce conservative global maxima to prevent misconfiguration.
- [x] Surface truncation metadata in client docs so callers understand pagination expectations.

## Testing & Documentation
- [x] Add integration tests for oversized responses, truncation metadata emission, and chunk continuation with invalid offsets.
- [x] Update developer documentation with the new limits, metadata fields, and chunking contract.
