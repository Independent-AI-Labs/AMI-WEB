# Browser Module Makefile

UV ?= uv
PYTHON_VERSION ?= 3.12

.PHONY: setup test clean

setup:
	@echo "Syncing browser dependencies..."
	$(UV) python install $(PYTHON_VERSION)
	$(UV) sync --dev
	@echo "Provisioning Chrome..."
	$(UV) run scripts/setup_chrome.py

test:
	$(UV) run pytest -q

clean:
	rm -rf .venv
