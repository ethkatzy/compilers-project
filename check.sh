#!/bin/bash
set -euo pipefail
cd "$(dirname "${0}")"
poetry run mypy .
poetry run ruff check .
poetry run pytest -vv tests/
