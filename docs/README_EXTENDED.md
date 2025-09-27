# Browser Module Reference

This document mirrors the current Browser module implementation inside AMI-ORCHESTRATOR.
It assumes readers understand the shared Base architecture (DataOps, FastMCP servers,
audit logging) and focuses on browser-specific pieces.

## Architecture Snapshot
- **Backend entrypoints** – `backend/core/` manages Chromium lifecycle, profile sandboxing,
  and CDP interactions. `backend/mcp/chrome/` exposes FastMCP tools that wrap these helpers.
- **Shared services** – No bespoke infrastructure lives here. Storage, audit logging, and security
  all delegate to `/base` utilities.
- **Research code** – Legacy anti-detection experiments and high-risk helpers are tagged under
  `web/` or `docs/research/`. Treat them as exploratory.

## Key Workflows
1. **Launch & interact via MCP**
   ```bash
   uv run --python 3.12 --project browser \
     python backend/mcp/chrome/run_chrome.py --transport stdio
   ```
   Tools exposed include navigation (`browser_navigate`), interaction (`browser_click`,
   `browser_type`), and state inspection (`browser_get_text`, `browser_screenshot`).

2. **Automated testing** – Use `scripts/run_tests.py` (see `../tests/README.md`). Integration
   tests rely on Chromium binaries installed by `scripts/setup_chrome.py`.

3. **Profile management** – `backend/core/profile_manager.py` handles per-run isolation.
   Profiles are stored in `data/profiles/` and are pruned by the cleanup routines in `backend/core/cleanup.py`.

## Development Guidelines
- Reuse Base abstractions (`UnifiedCRUD`, `SecurityContext`, audit helpers) for any new
  storage or security work.
- Keep JavaScript helpers under `backend/core/js/` and inject them via CDP commands – no inline
  script strings inside Python code.
- When experimenting with alternative detection countermeasures, document them under
  `docs/research/` to keep the production surface minimal.

## Research Archive
Long-form architecture analyses and historical anti-detection reports now live in
`docs/research/`. Update those notes only when you intentionally deviate from the current
implementation.
