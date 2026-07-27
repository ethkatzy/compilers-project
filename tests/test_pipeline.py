import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass

import pytest
from assembler import assemble_and_get_executable
from assembly_generator import generate_assembly
from ir_generator import GLOBAL_SYMTAB, generate_ir
from parser import parse
from tokenizer import tokenize


@dataclass
class ProgramCase:
    name: str
    source: str
    expected_stdout: str
    stdin: str | None = None


# Golden test programs covering the constructs documented in language_spec.html.
# Expected output for each was verified by actually assembling, linking, and
# running the generated program (see PROGRAMS-derived tests below) — not just
# hand-computed from the spec.
PROGRAMS = [
    ProgramCase("arithmetic_precedence",
                "print_int(1 + 2 * 3); print_int((1 + 2) * 3);", "7\n9\n"),
    ProgramCase("modulo_and_division",
                "print_int(17 % 5); print_int(17 / 5);", "2\n3\n"),
    ProgramCase(
        "comparisons",
        "print_bool(3 < 5); print_bool(5 <= 5); print_bool(2 > 9); "
        "print_bool(2 >= 9); print_bool(3 == 3); print_bool(3 != 3);",
        "true\ntrue\nfalse\nfalse\ntrue\nfalse\n",
    ),
    ProgramCase(
        "boolean_not", "print_bool(not true); print_bool(not false);", "false\ntrue\n"),
    ProgramCase("unary_minus",
                "print_int(-5 + 3); print_int(-(2 + 3));", "-2\n-5\n"),
    ProgramCase(
        "and_or_operators",
        "print_bool(true and false); print_bool(true and true); "
        "print_bool(false or true); print_bool(false or false);",
        "false\ntrue\ntrue\nfalse\n",
    ),
    ProgramCase("untyped_var_decl_and_assignment",
                "var x = 5; print_int(x); x = x + 1; print_int(x);", "5\n6\n"),
    ProgramCase("typed_int_var_decl", "var x: Int = 5; print_int(x);", "5\n"),
    ProgramCase("typed_bool_var_decl",
                "var b: Bool = true; print_bool(b);", "true\n"),
    ProgramCase("if_without_else", "if 1 < 2 then { print_int(99); }", "99\n"),
    ProgramCase("if_else_as_expression",
                "var x = if 3 < 5 then 1 else 2; print_int(x);", "1\n"),
    ProgramCase(
        "nested_block_shadowing",
        "var x = 1; { var x = 2; print_int(x); } print_int(x);",
        "2\n1\n",
    ),
    ProgramCase(
        "while_loop",
        "var i = 0; while i < 3 do { print_int(i); i = i + 1; }",
        "0\n1\n2\n",
    ),
    ProgramCase(
        "collatz",
        """
        var n: Int = 6;
        print_int(n);
        while n > 1 do {
            if n % 2 == 0 then {
                n = n / 2;
            } else {
                n = 3*n + 1;
            }
            print_int(n);
        }
        """,
        "6\n3\n10\n5\n16\n8\n4\n2\n1\n",
    ),
    ProgramCase("top_level_result_int", "1 + 2", "3\n"),
    ProgramCase("top_level_result_bool", "3 < 5", "true\n"),
    ProgramCase("read_int", "var n = read_int(); print_int(n + 1);",
                "42\n", stdin="41\n"),
    ProgramCase(
        "trailing_block_result_references_block_local",
        "{ var y = 5; y + 1 }",
        "6\n",
    ),
]

HAS_LINUX_TOOLCHAIN = shutil.which(
    "as") is not None and shutil.which("ld") is not None


@pytest.mark.parametrize("case", PROGRAMS, ids=[c.name for c in PROGRAMS])
def test_compiles_to_assembly_without_error(case: ProgramCase) -> None:
    """Portable smoke test: the full pipeline runs to completion and produces assembly text.

    Runs everywhere (no Linux `as`/`ld` needed) so it's part of every ./check.sh run.
    """
    tokens = tokenize(case.source)
    parsed = parse(tokens)
    ir_lines = generate_ir(GLOBAL_SYMTAB, parsed)
    assembly = generate_assembly(ir_lines)
    assert assembly.strip() != ""


@pytest.mark.skipif(
    not HAS_LINUX_TOOLCHAIN,
    reason="requires a real Linux x86-64 `as`/`ld` toolchain (assembler.py's internal correctness check)",
)
@pytest.mark.parametrize("case", PROGRAMS, ids=[c.name for c in PROGRAMS])
def test_program_produces_expected_output(case: ProgramCase) -> None:
    """End-to-end correctness check: assemble, link, and actually run the generated program.

    Uses assembler.py to invoke real `as`/`ld`, matching its documented role as an
    internal correctness check (see CLAUDE.md/ROADMAP.md). Skipped on platforms
    without a Linux assembler/linker on PATH, e.g. plain Windows without WSL.
    """
    tokens = tokenize(case.source)
    parsed = parse(tokens)
    ir_lines = generate_ir(GLOBAL_SYMTAB, parsed)
    assembly = generate_assembly(ir_lines)

    with tempfile.TemporaryDirectory() as workdir:
        assemble_and_get_executable(assembly, workdir=workdir)
        result = subprocess.run(
            [os.path.join(workdir, "a.out")],
            input=case.stdin,
            capture_output=True,
            text=True,
            timeout=10,
        )

    assert result.returncode == 0, result.stderr
    assert result.stdout == case.expected_stdout
