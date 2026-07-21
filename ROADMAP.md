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
| Empty out `src/compiler/__init__.py`'s leftover debug script | Ran a hardcoded demo at import time; currently crashes `poetry run main` because of the unqualified-import style. Not logic — just dead scratch code sitting in the package init. | Quick | Open |
| Remove `.test-gadget/` + `test-gadget.py` + `course.json` | Course-grading-submission infra; ~18MB of binaries, irrelevant to a public repo. Docker build already excludes `.test-gadget` via `.dockerignore`, confirming nothing else needs it. | Quick | **Done** |
| Remove `__main__.py` + `compiler.sh` + `Dockerfile` + `pyproject.toml` scripts entry | `__main__.py`'s CLI/serve entry point isn't something you wrote and isn't the "product" being shown — see Decisions above. All three other files exist only to support it. | Quick | **Done** |
| Stop tracking `.idea/` in git | PyCharm project files tracked in git — IDE-specific noise for a public repo. | Quick | Open |
| Tighten `.gitignore` | Missing `.venv/`, `.idea/`, `.ruff_cache/`, `.pytest_cache/`, `.claude/settings.local.json`. | Quick | Open |
| Replace stub tests (`tests/tokenizer_test.py` is a 2-line debug print, `tests/dummy_test.py` is a placeholder) | No real automated coverage exists yet. Could double as the home for an `assembler.py`-based "assemble and run" correctness check. | Medium | Open |
| Remove dead module-level demo code in `interpreter.py` | Was a hardcoded `while`-loop demo running on import. | — | **Done** (removed by user directly) |
| Decide on `instrinsics.py` → `intrinsics.py` rename | Genuine typo in a real, imported filename; fixing means updating every import site. Mechanical, not logic — needs explicit go-ahead since it touches `src/compiler/`. | Quick | Open |
| `check.sh` deletes `test_programs/workdir`, but no `test_programs/` exists | Leftover from an unfinished golden-file/end-to-end test approach. Drop the line or build the tests it implies. | Quick | Open |
| Resolve mypy import-resolution gap | `mypy_path` alone can't fix it — `__init__.py` makes mypy see `compiler` as a real package, conflicting with the flat unqualified-import style used everywhere. Real fix: package-qualified imports throughout `src/compiler/`, or `--explicit-package-bases`. | Medium | Open |
| Add a `LICENSE` file | No license currently exists. MIT is the common default for portfolio code. | Quick | Open |
| `interpreter.py` and `type_checker.py` are orphaned | Neither is called from `__init__.py`'s pipeline or `__main__.py`. `type_checker.py` is actively developed (most of recent git history) but not yet wired in — not a deletion candidate, a gap to close or a decision to make about scope. | — | Noted, no action yet |

---

## Documentation

| Item | Reasoning | Effort |
|---|---|---|
| Rewrite README framing | Current README is pure course setup instructions (pyenv/poetry, "submit to Test Gadget," "see the course page"). Needs reframing as a portfolio project. | Medium |
| Language spec summary | No spec exists anywhere. From the source: `var` declarations, `if/then/else`, `while/do`, `{ }` blocks, unary (`-`, `not`) and binary ops, function calls (`print_int`, `print_bool`, `read_int`), `Int`/`Bool`/`Unit` types. | Medium |
| Architecture overview | Explain the real pipeline: tokenizer → parser (recursive-descent → AST) → type checker (annotates types, currently unwired) → IR generator → assembly generator (x86-64 GNU-syntax text) → assembler (internal-only correctness check via `as`/`ld`). Note this targets x86-64 Linux specifically. | Quick-Medium |
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
