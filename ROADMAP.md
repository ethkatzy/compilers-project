# Public-Release Readiness Roadmap

Plan for turning this university compiler project into a public, CV-facing repo. Compiler/translation logic (tokenizer, parser, type checker, IR generator, assembly generator) is untouched throughout — everything here is scaffolding, docs, and presentation.

## Decisions made so far

- **`assembler.py` stays**, but repositioned: not a public-facing feature, kept as an internal correctness check (it invokes real `as`/`ld` to prove generated assembly actually assembles and runs). The public-facing product is the generated **assembly text**, not a compiled/running binary — that's the actual translation work and what you wrote.
- **`__main__.py` is being removed.** Cascading effects (traced, not assumed):
  - `compiler.sh` — pure wrapper around `poetry run main`; nothing left to wrap once `__main__.py` is gone. Remove alongside it.
  - `pyproject.toml`'s `[tool.poetry.scripts] main = "compiler.__main__:main"` — must be removed too, or Poetry's script entry points at a module that no longer exists.
  - `Dockerfile` — its `CMD` calls `__main__.py`'s `serve` mode, which was built specifically to talk to the course grading server (port 3000, matched the now-deleted `course.json`). Remove rather than patch; write a fresh one later if a web-frontend backend gets built.
  - `check.sh` — verified independent (only runs mypy/ruff/pytest). Not affected, stays as-is.
- **Removed:** `test-gadget.py`, `.test-gadget/` (3 platform binaries + `course.json`) — confirmed via repo-wide grep to have no references outside themselves and the README.
- **Removed:** `__main__.py`, `compiler.sh`, `Dockerfile`, and the `pyproject.toml` `[tool.poetry.scripts]` entry, all together (verified `poetry check` still passes with the entry gone). `check.sh` was left untouched — see below for why.
- **Still open:** README still documents all of the above (`./compiler.sh compile ...`, `./test-gadget.py submit`, editing `src/__main__.py`) — needs the doc rewrite from the Documentation section.

---

## Cleanup

| Item | Reasoning | Effort | Status |
|---|---|---|---|
| Empty out `src/compiler/__init__.py`'s leftover debug script | Ran a hardcoded demo at import time. Removed; `__init__.py` now only inserts its own directory onto `sys.path` so the submodules' unqualified sibling imports (`from tokenizer import ...`) resolve when the package is imported normally (`import compiler`), not just when a file inside it is run directly (e.g. via PyCharm's "run"). Verified both ways work. | Quick | **Done** |
| Remove `.test-gadget/` + `test-gadget.py` + `course.json` | Course-grading-submission infra; ~18MB of binaries, irrelevant to a public repo. Docker build already excludes `.test-gadget` via `.dockerignore`, confirming nothing else needs it. | Quick | **Done** |
| Remove `__main__.py` + `compiler.sh` + `Dockerfile` + `pyproject.toml` scripts entry | `__main__.py`'s CLI/serve entry point isn't something you wrote and isn't the "product" being shown — see Decisions above. All three other files exist only to support it. | Quick | **Done** |
| Stop tracking `.idea/` in git | PyCharm project files tracked in git — IDE-specific noise for a public repo. | Quick | **Done** |
| Tighten `.gitignore` | Missing `.venv/`, `.idea/`, `.ruff_cache/`, `.pytest_cache/`, `.claude/settings.local.json`. | Quick | **Done** |
| Replace stub tests (`tests/tokenizer_test.py` is a 2-line debug print, `tests/dummy_test.py` is a placeholder) | Replaced. `tests/tokenizer_test.py` now has real `tokenize()` unit tests. `tests/dummy_test.py` deleted. New `tests/test_pipeline.py` holds golden-program tests built from `language_spec.html`: a portable tier (tokenize→parse→generate_ir→generate_assembly, no OS deps, always runs) plus an `assembler.py`-based "assemble and run" tier that actually invokes `as`/`ld` and checks real stdout, gated on `shutil.which("as"/"ld")` so it's skipped where no Linux toolchain exists (this Windows dev box) and runs for real elsewhere (verified via WSL Ubuntu, which does have `as`/`ld`: all 45 tests pass, including real execution of the collatz example and `read_int`). | Medium | **Done** |
| Remove dead module-level demo code in `interpreter.py` | Was a hardcoded `while`-loop demo running on import. | — | **Done** (removed by user directly) |
| Decide on `instrinsics.py` → `intrinsics.py` rename | Genuine typo in a real, imported filename; fixing means updating every import site. Mechanical, not logic — needs explicit go-ahead since it touches `src/compiler/`. | Quick | **Done** |
| `check.sh` deletes `test_programs/workdir`, but no `test_programs/` exists | Leftover from an unfinished golden-file/end-to-end test approach. Dropped the line; no such directory has existed for a while, so the golden-file test idea can be revisited separately if wanted. | Quick | **Done** |
| Resolve mypy import-resolution gap | Fixed via `mypy_path = src/compiler` + `explicit_package_bases = True` in `mypy.ini` — keeps the unqualified-import style (no `from compiler.x import y` rewrite needed). `poetry run mypy .` now runs to completion instead of erroring on every unqualified import. It surfaces ~92 genuine type errors that were previously hidden behind the import-resolution noise — those are real bugs, not a config issue, and are a separate follow-up. | Medium | **Done** |
| Fix the ~92 genuine type errors mypy now surfaces | Uncovered once the import-resolution gap (above) was fixed and mypy could actually analyze the code instead of erroring on every unqualified import. Concentrated in `ir_generator.py` (the bulk of it — mostly "Incompatible types in assignment" against a `UnitType`-typed variable, and `Expression` missing attributes like `.name`/`.arguments`/`.function` where a subtype's field is accessed through the general `Expression` type), with smaller counts in `parser.py`, `astree.py`, `assembly_generator.py`, `datatypes.py`. `./check.sh` still fails on these — real pre-existing bugs, not a config issue. Not started. | Medium | Open |
| Add a `LICENSE` file | No license currently exists. MIT is the common default for portfolio code. | Quick | **Done** |
| Remove orphaned `interpreter.py` and `type_checker.py` | Neither was imported anywhere. Re-checked the "actively developed" assumption via `git log -- <file>`: `type_checker.py` had a single commit (the original scaffold) — the many "type checking" bug-fix commits actually all touched `ir_generator.py`, where that logic lives instead. `interpreter.py` was a tree-walking interpreter that predates the IR/codegen pipeline. Both deleted. | Quick | **Done** |

---

## Documentation

| Item | Reasoning | Effort |
|---|---|---|
| Rewrite README framing | Current README is pure course setup instructions (pyenv/poetry, "submit to Test Gadget," "see the course page"). Needs reframing as a portfolio project. | Medium |
| Language spec summary | `language_spec.html` (the original course page) now lives in the repo root and is the source of truth used to build `tests/test_pipeline.py`'s golden programs. Still needs turning into a proper portfolio-facing doc (it's currently a raw saved course page, with course-site CSS/JS/CDN references). | Medium |
| Architecture overview | Explain the real pipeline: tokenizer → parser (recursive-descent → AST, and where type checking actually happens — inline during IR generation, not a separate pass; see `interpreter.py`/`type_checker.py` removal above) → IR generator → assembly generator (x86-64 GNU-syntax text) → assembler (internal-only correctness check via `as`/`ld`). Note this targets x86-64 Linux specifically. | Quick-Medium |
| Build/run instructions | Rewrite once the `__main__.py`/`compiler.sh` question is settled — current instructions describe a CLI that's going away. | Quick |
| Examples + output | Add 1-2 full example programs with tokens/AST/IR/assembly shown, so a reader doesn't need to run anything. | Quick |
| Screenshots/demo link | Depends on the Frontend section below. | — |

---

## Frontend (pipeline visualizer)

Goal: input source → see tokens / AST / IR / assembly panels, like the lecturer's sandbox tool. Since `__main__.py` is going away, this now needs its own small backend rather than adapting `__main__.py`'s `serve` mode.

- **Backend**: small HTTP wrapper (Flask or stdlib) calling `tokenize()`, `parse()`, `generate_ir()`, `generate_assembly()` individually per stage. Dataclasses already give free `repr()`; `ir.Instruction.__str__` already formats nicely (e.g. `LoadIntConst(3, x1)`).
- **Frontend**: one static HTML page + vanilla JS + a textarea, four panels (Tokens, AST, IR, Assembly).
- **Explicitly out of scope for v1**: executing the compiled binary and showing program output. That's `assembler.py`'s job now (internal check only) — not something to expose to arbitrary public input without real sandboxing.

| Item | Effort |
|---|---|
| HTTP backend exposing the 4 pipeline stages as JSON | Quick-Medium |
| Static 4-panel frontend page | Quick-Medium |
| Nice-looking AST tree rendering | Quick |
| Visual polish for a CV-quality demo | Medium |

---

## Hosting / Deployment

`assembler.py` shells out to real `as`/`ld` and makes raw Linux x86-64 syscalls — that only runs on a real Linux x86-64 host, never in a browser. Since actually assembling/running is no longer part of the public-facing demo anyway (see Decisions), this stops being a hosting constraint at all.

**Recommended: Pyodide (CPython-in-WASM) + GitHub Pages.** Tokenizing, parsing, IR generation, and assembly-text generation are all pure Python with no subprocess/syscalls — Pyodide can run this entirely client-side, for free, with zero backend to maintain or secure. This exactly matches the "show the translation pipeline" goal.

- Depends on the `__init__.py` cleanup above (package must be cleanly importable before it can be loaded into Pyodide).
- Effort: **Medium** (mounting the package into Pyodide's virtual FS, wiring calls, marshalling results back to JS).

No backend hosting (Fly.io/Render/a VPS) is needed under this plan, since binary execution isn't part of what's being shown publicly.
