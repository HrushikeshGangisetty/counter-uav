# Developer entry points. Everything here runs with no hardware attached.
.PHONY: help setup test lint typecheck check arch fixtures clean

help:
	@echo "make setup      install dev dependencies into the active environment"
	@echo "make test       run the full pytest suite"
	@echo "make arch       run only the architecture/boundary enforcement tests"
	@echo "make lint       ruff"
	@echo "make typecheck  mypy"
	@echo "make check      lint + typecheck + test  (what CI runs)"
	@echo "make fixtures   regenerate deterministic replay fixtures"

setup:
	python -m pip install --upgrade pip
	python -m pip install -e ".[dev]"

test:
	python -m pytest

arch:
	python -m pytest tests/architecture -v

lint:
	python -m ruff check src tests simulation scripts
	python -m ruff format --check src tests simulation scripts

# MYPY_CACHE_DIR is overridable: mypy's sqlite cache fails on some network/synced
# filesystems. If you see 'sqlite3.OperationalError: disk I/O error', run
#   make typecheck MYPY_CACHE_DIR=/tmp/mypy-cache
MYPY_CACHE_DIR ?= .mypy_cache

typecheck:
	python -m mypy --cache-dir=$(MYPY_CACHE_DIR)

check: lint typecheck test

fixtures:
	python scripts/make_fixtures.py

clean:
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
	rm -rf .pytest_cache .mypy_cache .ruff_cache
