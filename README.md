# AMI Browser Module

Browser keeps agents connected to the real web with compliant, auditable Chromium automation. It delivers a ready-to-run FastMCP server so teams can add browsing superpowers without hand-rolling driver logic or compromising security controls.

## What You Get

This module packages the Chromium lifecycle manager, FastMCP tooling, and setup scripts that are used across the orchestrator. The sections below describe the components that ship today.

## What Exists Now

- `backend/core/` – Chrome lifecycle management (`ChromeManager`), profile isolation, and tool implementations.
- `backend/mcp/chrome/` – FastMCP server exposing launch/navigation/input/extraction/screenshot tools.
- `scripts/setup_chrome.py` – Installs Chromium/ChromeDriver binaries per platform with minimal sudo usage.
- `module_setup.py` – Delegates to Base `EnvironmentSetup`, ensuring dependencies install after the venv is created. Uses stdlib logging only.

## MCP Tools

`ChromeFastMCPServer` registers the following tool families (see `backend/mcp/chrome/tools/`):

- **Lifecycle** – `browser_launch`, `browser_list`, `browser_get_active`, `browser_terminate`.
- **Navigation** – `browser_navigate`, `browser_back`, `browser_forward`, `browser_refresh`, `browser_get_url`.
- **Input** – `browser_click`, `browser_type`, `browser_select`, `browser_hover`, `browser_scroll`, `browser_press`.
- **Extraction** – `browser_get_text`, `browser_exists`, `browser_wait_for`, `browser_get_attribute`, `browser_get_cookies`.
- **JavaScript** – `browser_evaluate`, `browser_execute`.
- **Screenshots** – `browser_screenshot`, `browser_element_screenshot`.

Each tool returns a Pydantic `BrowserResponse` so downstream callers receive structured results (status, payload, metadata).

## Running the Server

```bash
# stdio transport
uv run --python 3.12 --project browser python backend/mcp/chrome/run_chrome.py

# websocket transport
uv run --python 3.12 --project browser python backend/mcp/chrome/run_chrome.py --transport websocket --port 9000
```

Before launching, ensure Chromium exists:

```bash
uv run --python 3.12 --project browser python scripts/setup_chrome.py
```

`setup_chrome.py` respects `AMI_COMPUTE_PROFILE` (`cpu`, `nvidia`, `intel`, `amd`) when choosing driver bundles.

## Testing

```bash
uv run --python 3.12 --project browser python scripts/run_tests.py
```

The test runner executes Base’s Python suite followed by optional npm-based checks when present. Browser integration tests require Chromium; they will skip gracefully if the binary is missing.

## Configuration

- `config.yaml` – Created from the platform template on first setup. Controls binary paths, headless options, proxy settings, and profile locations.
- Environment hints inherit from the orchestrator (`AMI_HOST`, compute profiles, etc.).

## Compliance & Roadmap Notes

- The module’s audit hooks integrate with Base logging utilities; map them to the compliance backend once `compliance/backend` is implemented.
- Future work: surface generated session artefacts (screenshots, logs) through the compliance MCP server so evidence can be attached to controls.

Refer to `docs/Architecture-Map.md` at the repository root for module relationships, and `compliance/docs/research/COMPLIANCE_BACKEND_SPEC.md` for the upcoming compliance integration requirements.
