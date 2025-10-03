# Browser Module Test Guide

Tests run under the shared orchestrator toolchain. Use the module runner so paths and
FastMCP dependencies mirror production:

```bash
uv run --python 3.12 --project browser python scripts/run_tests.py
```

## Test Suites
- **Unit & service tests** – Cover lifecycle management, CDP helpers, and utility functions.
- **Integration (FastMCP)** – Located in `tests/integration/` and exercise `backend/mcp/chrome`.
  These tests require Chromium and ChromeDriver; install them with
  `uv run --python 3.12 --project browser python scripts/setup_chrome.py` before running.

## Running Individual Tests
```bash
# focus on integration
uv run --python 3.12 --project browser \
  python scripts/run_tests.py tests/integration/test_chrome_manager.py

# run pytest directly when inside the venv
pytest tests/unit/test_navigation.py -k awaiters
```

## Anti-Detection Regression (Research)
The anti-detection research scenarios live under `tests/integration/test_antidetection.py`.
They are maintained as research coverage; they may require manual updates to reflect the
current fingerprinting strategy.
