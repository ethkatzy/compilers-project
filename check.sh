#!/bin/bash
set -euo pipefail
cd "$(dirname "${0}")"
poetry run mypy .
rm -Rf test_programs/workdir
poetry run pytest -vv tests/
