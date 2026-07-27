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
| Fix the ~92 genuine type errors mypy now surfaces | Uncovered once the import-resolution gap (above) was fixed and mypy could actually analyze the code instead of erroring on every unqualified import. Fixed in six passes, each verified against the full test suite (Windows pytest + WSL's `as`/`ld`-backed execution tier) to confirm no behavior changed: (1) a `t = Unit`-narrowing bug repeated ~44 times in `ir_generator.py`, fixed by annotating each first-occurrence as `t: Type`; (2) `visit()`'s genuine `IRVar \| SymTab` return type wasn't narrowed at call sites expecting a plain `IRVar` — added `assert isinstance(...)` at each; (3) `astree.py`/`parser.py` used the `UnitType` *class* instead of an instance as a default/sentinel value (`field(default=UnitType)`), which in turn caused `ir_generator.py`'s `type == UnitType` sentinel checks to silently misbehave — both fixed together, catching one previously-latent bug along the way (a `read_int` test failure that surfaced once the sentinel bug was fixed and immediately exposed the dependent code); (4) missing return-type annotations on `__repr__`/`__eq__`/`__len__`/`new_var`; (5) two missing-return-statement gaps in `parser.py` (`prev()`, `final_statement()`); (6) a `dict[(K, V), X]` syntax error (should be `dict[tuple[K, V], X]`). `poetry run mypy .` now reports zero errors. | Medium | **Done** |
| Fix the ~30 ruff findings (`./check.sh`'s lint stage) | Mostly unsorted/unused imports and whitespace, auto-fixed via `ruff check --fix`; a handful fixed by hand — `assembler.py`'s two generic helper functions moved to PEP 695 syntax (`def f[T](...)`), unused match-pattern bindings dropped in `assembly_generator.py`, one over-120-char f-string wrapped in `parser.py`. `poetry run ruff check .` now reports zero findings. `./check.sh` passes end-to-end for the first time. | Quick | **Done** |
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

**Done.** Goal: input source → see tokens / AST / IR / assembly panels, like the lecturer's sandbox tool. Built with no backend at all — runs the real pipeline client-side in the browser via Pyodide (CPython-in-WASM), superseding the originally-planned "small HTTP wrapper" (see Hosting/Deployment below, which is where that decision actually got made).

- `frontend/index.html` / `style.css` / `app.js` — a static page, vanilla JS, a source textarea, and four panels (Tokens, AST, IR, Assembly) in a responsive 2×2 grid that collapses to tabs on narrow viewports. Dark/light themed via `prefers-color-scheme`.
- `frontend/py/webapi.py` — glue module (not compiler logic) loaded into Pyodide's virtual FS. Runs `tokenize()` → `parse()` → `generate_ir(GLOBAL_SYMTAB, ...)` → `generate_assembly()` stage by stage, catching each stage's exception independently, and serializes tokens/AST/IR/assembly to JSON for `app.js` to render. The IR panel is labeled "includes type checking" since that's genuinely where it happens (inline in `generate_ir`, not a separate pass).
- `frontend/build.py` — assembles a deployable `_site/` from the frontend assets plus the 8 compiler modules the 4 exposed stages actually need (`tokenizer.py`, `datatypes.py`, `intrinsics.py`, `ir.py`, `astree.py`, `parser.py`, `ir_generator.py`, `assembly_generator.py`). `assembler.py` is deliberately excluded — it shells out to real `as`/`ld` and stays internal-only, per the out-of-scope decision below. Same script runs for local dev (`python frontend/build.py` + `python -m http.server` from `_site/`) and in CI, so there's no dev/prod path branching.
- AST rendering walks `dataclasses.fields()` recursively into native `<details>/<summary>` elements — collapsible for free, no tree library needed.
- Parser/IR-generator errors are plain `Exception(f"{loc}: message")` strings; `app.js` regexes out the `Location(line=.., column=..)` repr to show a cleaned-up message and a "Jump to location" button that moves the textarea cursor there.
- **Explicitly out of scope for v1** (unchanged from the original plan): executing the compiled binary and showing program output. That's `assembler.py`'s job (internal check only) — not something to expose to arbitrary public input without real sandboxing.

| Item | Status |
|---|---|
| 4-stage pipeline glue (`webapi.py`), typed and ruff-clean | **Done** |
| Static 4-panel frontend page, responsive grid/tabs, dark+light theme | **Done** |
| Collapsible AST tree rendering | **Done** |
| Per-stage error handling with click-to-locate in the source | **Done** |
| Example-program dropdown (pulled from `tests/test_pipeline.py`'s golden programs) + localStorage persistence | **Done** |

---

## Hosting / Deployment

**Done — Pyodide + GitHub Pages, as recommended below, no backend built.** `assembler.py` shells out to real `as`/`ld` and makes raw Linux x86-64 syscalls — that only runs on a real Linux x86-64 host, never in a browser. Since actually assembling/running was never part of the public-facing demo (see Decisions and Frontend above), this was never a hosting constraint.

Tokenizing, parsing, IR generation, and assembly-text generation are all pure Python with no subprocess/syscalls (confirmed by checking every `import` line in `src/compiler/`), so Pyodide runs the pipeline entirely client-side, for free, with zero backend to maintain or secure.

- `.github/workflows/deploy-pages.yml` runs `frontend/build.py` then publishes `_site/` via `actions/upload-pages-artifact` + `actions/deploy-pages` on every push to `main` that touches `frontend/` or `src/compiler/`.
- **Still open:** enabling Pages itself is a one-time manual step — repo Settings → Pages → Source = GitHub Actions. Not something that can be done from a commit.

No backend hosting (Fly.io/Render/a VPS) was needed, since binary execution isn't part of what's shown publicly.
