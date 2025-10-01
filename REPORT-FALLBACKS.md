# Banned Keyword Audit – Browser Module

_No occurrences of the deprecated keyword remain within `browser/` as of 2025-10-01T22:08:26Z._

## Recent Remediation Highlights
- Removed the Brave backup pipeline: web search now uses a single, explicitly-configured provider and surfaces hard failures for unreachable engines.
- Hardened setup and lifecycle flows so Chrome binaries must be declared up front; the module no longer auto-discovers system installs or copies templates behind the user's back.
- Eliminated secondary execution paths (e.g., direct script injection, port auto-selection) that previously masked launch issues; these now raise actionable errors.
- Updated documentation, configuration templates, and generated metadata to reflect the explicit-provider requirement.
- Reworked fixtures/tests to skip cleanly when prerequisites are missing instead of silently swapping to local services.

## Verification
- Run the banned-word scanner for the `browser/` module.
- `uv run --python 3.12 --project browser python scripts/run_tests.py`
