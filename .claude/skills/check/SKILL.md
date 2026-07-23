---
name: check
description: Run the project's verification suite (mypy strict typing + pytest) via ./check.sh and summarize the results. Use when the user asks to verify, check, or validate the compiler, or before reporting a fix/feature as complete if they've asked for confirmation.
---

Run `./check.sh` from the repository root (it runs `poetry run mypy .`, `poetry run ruff check .`, then `poetry run pytest -vv tests/`).

Report back concisely:
- Whether mypy passed; if not, list the file:line and error for each failure.
- Whether pytest passed; if not, list which tests failed and the assertion/error for each.
- Do not paste the full raw output — summarize it.
