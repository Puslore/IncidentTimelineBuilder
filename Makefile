.PHONY: help setup test coverage check build-lib clean

help: ## Display this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

setup: ## Set up local virtual environment and install dependencies
	python -m venv .venv
	.venv/bin/pip install -r requirements-dev.txt

test: ## Run unit and smoke tests
	PYTHONPATH=packages/core/src pytest tests/ -v

coverage: ## Run tests and print coverage report
	PYTHONPATH=packages/core/src pytest tests/ -v --cov=packages/core/src/timeline_core --cov-report=term-missing

check: ## Run type checking and lint checks
	PYTHONPATH=packages/core/src mypy packages/core/src/timeline_core

build-lib: ## Build core library package
	cd packages/core && python -m build

docs: ## Generate project documentation message
	@echo "Documentation is available in markdown format under docs/ directory."

compose-up: ## Run the timeline builder inside docker container using compose
	docker compose -f infra/compose.yaml up --build

compose-down: ## Shut down the docker compose services
	docker compose -f infra/compose.yaml down

install-lib-local: ## Install built core library wheel locally into active environment
	pip install --force-reinstall packages/core/dist/*.whl

publish-lib: ## Publish core library package to PyPI (TestPyPI configuration)
	python -m twine upload --repository testpypi packages/core/dist/*

clean: ## Clean up temporary and build directories
	rm -rf .pytest_cache .coverage htmlcov .mypy_cache build dist packages/core/build packages/core/dist packages/core/*.egg-info
