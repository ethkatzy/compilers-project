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
- `mypy.ini` also sets `mypy_path = src/compiler` and `explicit_package_bases = True` so mypy resolves the unqualified sibling imports (`from tokenizer import ...`) instead of erroring with "Cannot find implementation... for module named X". Without `explicit_package_bases`, mypy's normal package-root-finding (walking up from `src/compiler/__init__.py`) collides with `mypy_path` pointing at the same directory and fails with "Source file found twice under different module names". Don't remove either setting without re-testing `poetry run mypy .` from a clean run.
- Modules use unqualified imports (e.g. `import astree as ast`, `from datatypes import Int, Bool`), not `from compiler.x import y`. Keep new modules consistent with this style rather than switching to package-qualified imports. At runtime this works because `src/compiler/__init__.py` inserts its own directory onto `sys.path` — but only once `compiler` itself has been imported. `tests/conftest.py` does the same `sys.path` insertion directly (pytest loads conftest.py before collecting tests), so test files can also use unqualified imports (`from tokenizer import tokenize`) without needing to `import compiler` first. `pytest.ini_options`'s `pythonpath = "src"` is unrelated to this — it only makes `import compiler` itself resolve, not the unqualified imports inside its submodules.
- AST/token/type nodes are `@dataclass`. AST dispatch (e.g. in `ir_generator.py`) uses `match`/`case` structural pattern matching over `astree` node types — follow this pattern when adding new node handling rather than isinstance chains.
- `src/compiler/instrinsics.py`'s typo (missing the "n") has been fixed — it's now `intrinsics.py`, with all import sites updated to match.

## Tests

- `tests/tokenizer_test.py` has real `tokenize()` unit tests. `tests/test_pipeline.py` has golden-program tests (source drawn from `language_spec.html`) run through the full pipeline. It has two tiers: a portable one (tokenize→parse→generate_ir→generate_assembly must complete without error, no OS deps, always runs) and an execution one (`assembler.py` actually invokes `as`/`ld` to assemble+link+run the program and checks real stdout) that's skipped via `shutil.which("as"/"ld")` when no Linux toolchain is on PATH — which is the normal case on plain Windows. To actually exercise the execution tier on a Windows dev box, run pytest from inside a Linux environment that has `as`/`ld` (e.g. `wsl -d <distro> -- bash -lc 'cd /mnt/c/... && PYTHONPATH=src/compiler python3 -m pytest tests/'`, if a WSL distro is available).

## Cleanup in progress

- Ruff (`[tool.ruff]` in `pyproject.toml`, `line-length = 120`) was just added and currently reports ~43 pre-existing findings (mostly unused variables and unsorted imports) — `./check.sh` will fail on these until they're fixed; this is expected backlog, not a regression from your current change.
- `poetry run mypy .` no longer fails on import resolution (see the `mypy_path`/`explicit_package_bases` note above) — it now runs to completion and surfaces genuine type errors in the code (~92, across `astree.py`, `parser.py`, `ir_generator.py`, `assembly_generator.py`, `datatypes.py`; see ROADMAP.md for a breakdown). Those are real pre-existing type bugs, not a config problem, and are unfixed — `./check.sh` will still fail on them until they're addressed.
