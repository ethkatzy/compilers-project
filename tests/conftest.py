import sys
from pathlib import Path

# The compiler submodules use unqualified sibling imports (e.g. `from tokenizer
# import ...`), matching the project convention (see CLAUDE.md). Insert the
# package directory directly so test files can import them the same way,
# without needing to import `compiler` first to trigger its own sys.path fix.
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "compiler"))
