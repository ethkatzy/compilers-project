# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

A hand-written Python compiler (no ANTLR/PLY/lark): lexer → recursive-descent parser → type checker → IR → assembly codegen, in `src/compiler/`. Originally a university compilers-course scaffold; it's now being cleaned up for general use, so course-specific coupling should be removed rather than preserved.

## Setup & commands

- Dependency management is Poetry; Python version is pinned via pyenv (`.python-version`, 3.12).
- `poetry install` to set up the environment.
- `./check.sh` — runs `poetry run mypy .`, `poetry run ruff check .`, then `poetry run pytest -vv tests/`. This is the canonical local verification command.
- There is no CLI entry point anymore: `__main__.py`, `compiler.sh`, the `Dockerfile`, and the `pyproject.toml` `[tool.poetry.scripts]` entry were all removed together (they only existed to support a course-grading `serve` mode, not something the user wrote). The pipeline is used by calling `tokenize()` → `parse()` → `generate_ir()` → `generate_assembly()` directly; see `src/compiler/__init__.py` for the reference chain. `assembler.py` still exists but only as an internal correctness check (it shells out to real `as`/`ld` to prove generated assembly is valid) — it is not wired into any public entry point.

## Code conventions

- `mypy.ini` sets `disallow_untyped_defs` and `disallow_untyped_calls` — all functions need full type hints, including on internal helpers, not just public APIs.
- Modules use unqualified imports (e.g. `import astree as ast`, `from datatypes import Int, Bool`), not `from compiler.x import y`. This works because `pytest.ini_options` sets `pythonpath = "src"` and Poetry installs `compiler` such that its submodules resolve as top-level imports. Keep new modules consistent with this style rather than switching to package-qualified imports.
- AST/token/type nodes are `@dataclass`. AST dispatch (e.g. in `type_checker.py`) uses `match`/`case` structural pattern matching over `astree` node types — follow this pattern when adding new node handling rather than isinstance chains.
- `src/compiler/instrinsics.py` is misspelled (missing the "n") but is the real, in-use filename — don't "fix" the typo without updating every import site, and don't create a correctly-spelled duplicate.

## Cleanup in progress

- `tests/tokenizer_test.py` is a stub left over from debugging (two lines, no `test_*` functions) — it is not real tokenizer coverage despite the name.
- `tests/dummy_test.py` is a placeholder (`assert 1 + 1 == 2`) meant to be replaced once real tests exist.
- Ruff (`[tool.ruff]` in `pyproject.toml`, `line-length = 120`) was just added and currently reports ~43 pre-existing findings (mostly unused variables and unsorted imports) — `./check.sh` will fail on these until they're fixed; this is expected backlog, not a regression from your current change.
- `poetry run mypy .` currently fails with ~269 import-not-found errors, unrelated to ruff: `mypy.ini` has no `mypy_path`, and the codebase's unqualified sibling imports (`from tokenizer import ...` inside `src/compiler/`) don't resolve without one. Adding `mypy_path = src` alone doesn't fix it either — `src/compiler/__init__.py` makes mypy see `compiler` as a real package, so pointing `mypy_path` at `src/compiler` too creates a "found twice under different module names" conflict. Fixing this for real means either switching to package-qualified imports (`from compiler.tokenizer import ...`) throughout `src/compiler/`, or using `--explicit-package-bases` with a restructure — worth deciding deliberately as part of the cleanup rather than patching mypy.ini in isolation.
