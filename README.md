
## Setup

Requirements:

- [Pyenv](https://github.com/pyenv/pyenv) for installing Python 3.12+
    - Recommended installation method: the "automatic installer"
      i.e. `curl https://pyenv.run | bash`
    - Follow the instructions at the end of the output to make pyenv available in your shell.
      You may need to restart your shell or even log out and log in again to make
      the `pyenv` command available.
- [Poetry](https://python-poetry.org/) for installing dependencies
    - Recommended installation method: the "official installer"
      i.e. `curl -sSL https://install.python-poetry.org | python3 -`

Install dependencies:

    # Install Python specified in `.python-version`
    pyenv install
    # Install dependencies specified in `pyproject.toml`
    poetry install

If `pyenv install` gives an error about `_tkinter`, you can ignore it.
If you see other errors, you may have to investigate.

If you have trouble with Poetry not picking up pyenv's python installation,
try `poetry env remove --all` and then `poetry install` again.

Typecheck and run local unit tests:

    ./check.sh
    # or individually:
    poetry run mypy .
    poetry run pytest -vv

Once you've finished your compiler, edit `src/__main__.py` to call your compiler in function `call_compiler`.
Then you can run your compiler on a source code file like this:

    ./compiler.sh compile path/to/source/code --output=path/to/output/file

You can send the finished compiler to Test Gadget for evaluation with:

    ./test-gadget.py submit

See the course page for more information.

## IDE setup

Recommended VSCode extensions:

- Python
- Pylance
- autopep8
