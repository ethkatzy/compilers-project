import sys
from pathlib import Path

# The submodules use unqualified sibling imports (e.g. `from tokenizer import ...`),
# so this package's own directory must be on sys.path for `import compiler` to work.
sys.path.insert(0, str(Path(__file__).parent))
