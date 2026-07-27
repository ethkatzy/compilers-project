"""Assembles the deployable pipeline-visualizer site into _site/.

Run locally (`poetry run python frontend/build.py`) and serve _site/ with
`python -m http.server` for dev testing, or run in CI before publishing to
GitHub Pages -- both produce the identical layout app.js expects, so
there's no dev/prod path branching.
"""

import shutil
from pathlib import Path

FRONTEND_DIR = Path(__file__).parent
REPO_ROOT = FRONTEND_DIR.parent
COMPILER_SRC = REPO_ROOT / "src" / "compiler"
OUTPUT_DIR = REPO_ROOT / "_site"

STATIC_FILES = ["index.html", "style.css", "app.js"]

# The pipeline stages the visualizer exposes only need these modules.
# assembler.py is deliberately excluded: it shells out to real `as`/`ld`
# and isn't part of the public-facing demo.
COMPILER_MODULES = [
    "tokenizer.py",
    "datatypes.py",
    "intrinsics.py",
    "ir.py",
    "astree.py",
    "parser.py",
    "type_checker.py",
    "ir_generator.py",
    "assembly_generator.py",
]


def build() -> None:
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True)

    for name in STATIC_FILES:
        shutil.copy2(FRONTEND_DIR / name, OUTPUT_DIR / name)

    py_dir = OUTPUT_DIR / "py"
    py_dir.mkdir()

    for name in COMPILER_MODULES:
        shutil.copy2(COMPILER_SRC / name, py_dir / name)
    shutil.copy2(FRONTEND_DIR / "py" / "webapi.py", py_dir / "webapi.py")

    print(f"Built site at {OUTPUT_DIR}")


if __name__ == "__main__":
    build()
