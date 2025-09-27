# FastMCP Integration Test Notes

The integration suite targets `backend/mcp/chrome`, which builds on the shared Base
FastMCP infrastructure. To avoid import issues, always run these tests through the
module runner so the parent `/base` package is on `sys.path`.

```bash
uv run --python 3.12 --project browser \
  python scripts/run_tests.py tests/integration/test_mcp_*
```

## Pre-requisites
1. Install Chromium + ChromeDriver via `uv run --python 3.12 --project browser python scripts/setup_chrome.py`.
2. Ensure the Base module is installed in editable mode; the module runner handles this automatically.
3. Provide any required environment variables in `browser/.env` (see `README.md`).

## Common Issues
- **ImportError for `base.backend`** – Indicates the tests were invoked directly with `pytest`.
  Re-run through the module runner or add the repository root to `PYTHONPATH` before execution.
- **Chrome binary missing** – Re-run `scripts/setup_chrome.py` or point `BROWSER_CHROME_PATH`
  to an existing binary.

Legacy Windows-only instructions have been removed. Tests now work cross-platform
as long as the commands above are used.
