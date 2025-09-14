Mypy Status

- Status: FAIL — tests contain many typing issues (dozens), code under `backend/` mostly OK.

Top Error Themes

- Missing return type annotations in tests: add `-> None` or concrete types.
- Unsafe indexing/collection assumptions in tests: add precise types or casts where safe.
- Utilities using `browser.driver` without None-guards: fixed in `tests/utils/browser_utils.py` by asserting driver non-None.
- Removed any relaxers: no `ignore_errors`, tests included in checks.

Immediate Fixes Applied

- Added package `__init__` files for test packages; converted imports to `browser.tests.*` to avoid duplicate module names.
- Added annotations in `tests/unit/fixtures.py` and hardened `tests/utils/browser_utils.py`.
- Removed `type: ignore` on `yaml` import in `module_setup.py`.

Next Fixes (short list)

- Annotate functions in:
  - `tests/unit/test_browser_properties.py` (multiple `-> None`, collection types).
  - `tests/fixtures/threaded_server.py` (loop types and returns).
  - `tests/unit/test_mcp_protocol.py` and `test_chrome_manager.py` (return types on tests, index usage over `Collection`).

Verification Rules (Do Not Skip)

- Do not exclude tests or add `ignore_errors` blocks.
- Keep strict settings; add explicit types and runtime checks instead.

