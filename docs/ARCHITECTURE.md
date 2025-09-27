# Browser Architecture Overview

This overview reflects the current Browser module structure inside AMI-ORCHESTRATOR.
For shared infrastructure details (DataOps, security, audit logging), refer to `/base`.

## Module Layout
```
browser/
├── backend/
│   ├── core/            # Chromium lifecycle, profile management, CDP helpers
│   ├── mcp/chrome/      # FastMCP server + tool implementations
│   └── models/          # Pydantic contracts shared by MCP tools
├── scripts/             # Setup and runner scripts
├── tests/               # Unit + FastMCP integration suites
└── web/                 # Research sandboxes (anti-detection experiments)
```

## Runtime Flow
1. **Chromium provisioning** – `scripts/setup_chrome.py` fetches platform-specific binaries.
2. **Server boot** – `backend/mcp/chrome/run_chrome.py` registers FastMCP tools and exposes
   stdio or WebSocket transports.
3. **Operations** – Tools call into `backend/core/*` for browser creation, navigation, and
   artifact capture. Responses are serialized Pydantic models.
4. **Persistence & logging** – Any data persistence or audit logging must reuse `/base`
   services; the browser module itself does not define storage engines.

## Development Notes
- Keep new services stateless; rely on Base DAO factories when persistence is unavoidable.
- Annotate all asynchronous flows (async `def`) and respect the lint/type settings enforced by
  the orchestrator pre-commit hooks.
- Experimental flows belong under `web/` with corresponding notes in `docs/research/`.

Historical diagrams have been moved to `docs/research/` for reference.
