# Contributing to the Browser Module

This module lives inside the AMI-ORCHESTRATOR monorepo and shares tooling with `/base`.
Follow the steps below to stay aligned with the platform direction.

## Workflow Essentials
- Work on branch `main` (no detached HEADs).
- Use the orchestrator pre-commit hooks; never pass `--no-verify`.
- Run tests via the module runner: `uv run --python 3.12 --project browser python scripts/run_tests.py`.
- Keep imports and service code consistent with `/base` (DataOps models, FastMCP servers,
  audit logging helpers). If you need an experimental path, place it under a clearly labeled
  `research` directory and document the deviation.

## Environment Setup
```bash
# from repo root
uv run --python 3.12 module_setup.py browser

# activate the venv if you want an interactive shell
source browser/.venv/bin/activate  # (Linux/macOS)
#   or
browser\.venv\Scripts\activate    # (Windows)
```

`module_setup.py` delegates to `base.backend.utils.environment_setup.EnvironmentSetup`,
so the same uv workflows, hooks, and tool versions apply across every module.

## Making Changes
1. **Coding standards** – Ruff + mypy run automatically. Prefer stdlib `logging` and Base helpers
   over third-party logging or bespoke infrastructure.
2. **Tests** – Add unit/integration tests under `browser/tests/`. The FastMCP suite can be
   exercised with `uv run --python 3.12 --project browser python scripts/run_tests.py tests/integration`.
3. **Documentation** – Update `browser/README.md` or inline docs to match the actual code. Long-form
   architecture notes belong under `browser/docs/`.
4. **Commit** – Ensure hooks pass, then `git commit`. Push straight to `main` when green.

## CI/DI Hooks
The orchestrator pipeline executes:
- `python scripts/run_tests.py` (from repo root) – delegates to each module runner.
- Pre-commit hooks configured in `/base` – ruff, ruff-format, mypy, large-file checks.

No additional CI configuration is required inside the browser module; reuse the shared tooling.
