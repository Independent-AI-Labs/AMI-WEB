# Browser Module — Setup Contract

Delegation
- `module_setup.py` must delegate to Base’s `AMIModuleSetup` to create `.venv`, install Base + Browser requirements, and install hooks.

Entrypoints
- Runner: `browser/scripts/run_chrome.py` performs all path setup; application code does not modify `sys.path`.

Known deviations (to correct)
- Top-level imports in `module_setup.py` include `yaml` and `loguru` before venv creation. Replace with stdlib `logging` until after dependencies are installed, or import lazily inside functions executed post-install.

Chrome tooling
- Post-setup, `module_setup.py` may perform Chrome/ChromeDriver provisioning. Keep third-party imports deferred; use subprocess and stdlib to run `scripts/setup_chrome.py`.

Policy references
- Orchestrator contract: `/docs/Setup-Contract.md`
- Base setup utilities: `base/backend/utils/{path_finder.py, environment_setup.py, path_utils.py}`
