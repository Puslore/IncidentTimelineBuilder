VENV = .venv
VENV_BIN_DIR := $(shell python -c "import sys; print('Scripts' if sys.platform == 'win32' else 'bin')" 2>/dev/null || python3 -c "import sys; print('Scripts' if sys.platform == 'win32' else 'bin')" 2>/dev/null || echo bin)
VENV_BIN = $(VENV)/$(VENV_BIN_DIR)

PYTHON = $(VENV_BIN)/python
PIP = $(VENV_BIN)/pip

.PHONY: help setup shell test coverage check build-lib docs diagrams compose-up compose-down install-lib-local publish-lib clean

help: ## Display this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

$(VENV_BIN)/activate: requirements-dev.txt
	python -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements-dev.txt
	touch $(VENV_BIN)/activate

setup: $(VENV_BIN)/activate ## Set up local virtual environment and install dependencies

shell: $(VENV_BIN)/activate ## Enter the virtual environment shell
	@echo "entering venv, type exit to quit"
	@PATH=$(shell pwd)/$(VENV_BIN):$$PATH bash

test: $(VENV_BIN)/activate ## Run unit and smoke tests
	PYTHONPATH=packages/core/src $(PYTHON) -m pytest tests/ -v

coverage: $(VENV_BIN)/activate ## Run tests and print coverage report
	PYTHONPATH=packages/core/src $(PYTHON) -m pytest tests/ -v --cov=packages/core/src/timeline_core --cov-report=term-missing --cov-report=html

check: $(VENV_BIN)/activate ## Run type checking and lint checks
	PYTHONPATH=packages/core/src $(PYTHON) -m mypy packages/core/src/timeline_core

build-lib: $(VENV_BIN)/activate ## Build core library package
	$(PYTHON) -m build packages/core

docs: $(VENV_BIN)/activate ## Generate project documentation (Sphinx HTML build)
	$(PYTHON) -m sphinx -b html docs/ docs/_build/html

diagrams: $(VENV_BIN)/activate ## Generate SVG and PNG diagrams using Docker mermaid-cli
	$(PYTHON) -c "import os; os.makedirs('docs/_generated', exist_ok=True)"
	docker run --rm --user root -v "$(CURDIR):/data" minlag/mermaid-cli -i /data/docs/diagrams/class_diagram.mermaid -o /data/docs/_generated/class_diagram.svg
	docker run --rm --user root -v "$(CURDIR):/data" minlag/mermaid-cli -i /data/docs/diagrams/class_diagram.mermaid -o /data/docs/_generated/class_diagram.png
	docker run --rm --user root -v "$(CURDIR):/data" minlag/mermaid-cli -i /data/docs/diagrams/sequence_diagram.mermaid -o /data/docs/_generated/sequence_diagram.svg
	docker run --rm --user root -v "$(CURDIR):/data" minlag/mermaid-cli -i /data/docs/diagrams/sequence_diagram.mermaid -o /data/docs/_generated/sequence_diagram.png
	docker run --rm --user root -v "$(CURDIR):/data" minlag/mermaid-cli -i /data/docs/diagrams/architecture_diagram.mermaid -o /data/docs/_generated/architecture_diagram.svg
	docker run --rm --user root -v "$(CURDIR):/data" minlag/mermaid-cli -i /data/docs/diagrams/architecture_diagram.mermaid -o /data/docs/_generated/architecture_diagram.png

compose-up: ## Run the timeline builder inside docker container using compose
	docker compose -f infra/compose.yaml up --build

compose-down: ## Shut down the docker compose services
	docker compose -f infra/compose.yaml down

install-lib-local: $(VENV_BIN)/activate ## Install built core library wheel locally into active environment
	$(PIP) install --force-reinstall packages/core/dist/*.whl

publish-lib: $(VENV_BIN)/activate ## Publish core library package to PyPI (TestPyPI configuration)
	$(PYTHON) -m twine upload --repository testpypi packages/core/dist/*

clean: ## Clean up temporary and build directories
	rm -rf .pytest_cache .coverage htmlcov .mypy_cache build dist packages/core/build packages/core/dist packages/core/*.egg-info docs/_build docs/_generated

