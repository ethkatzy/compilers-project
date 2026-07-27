from dataclasses import dataclass

import pytest
from ir_generator import GLOBAL_SYMTAB, generate_ir
from parser import parse
from tokenizer import tokenize


@dataclass
class RejectCase:
    name: str
    source: str
    spec_basis: str
    expected_message: str


# Baseline for the ir/type-checker split: each case is a program that should be
# statically rejected. `spec_basis` is the language_spec.md "Semantics" clause
# (or, where noted, an implementation-defined static rule not literally in the
# spec) that the program violates. `expected_message` is a regex matched against
# the exception raised by generate_ir(), which now delegates its type checking
# to type_checker.type_check() (see ir_generator.py) rather than validating
# inline, so this doubles as a regression test for type_checker.py's wording.
REJECTS = [
    RejectCase(
        "redeclared_variable_same_scope",
        "var x = 1; var x = 2;",
        'Variable declaration: "if C already has a local ID, fail"',
        "already declared",
    ),
    RejectCase(
        "undeclared_identifier_reference",
        "x;",
        'Identifier lookup: "look up ID from C, fail if not found"',
        "Unknown identifier",
    ),
    RejectCase(
        "assignment_to_undeclared_variable",
        "x = 5;",
        'Assignment E1=E2: "if C\' is still not defined, fail"',
        "Unknown identifier",
    ),
    RejectCase(
        "assignment_to_non_identifier",
        "1 = 2;",
        'Assignment E1=E2: "if E1 is not an identifier, fail"',
        "must be a variable",
    ),
    RejectCase(
        "assignment_type_mismatch",
        "var x = 1; x = true;",
        "Implementation-defined: assignment target's declared type must match "
        "the assigned value's type (spec doesn't state this for static typing, "
        "but it's the natural static reading of the assignment semantics)",
        "expects Int, got Bool",
    ),
    RejectCase(
        "unary_minus_on_bool",
        "-true;",
        'Unary "-E": "if the value of E is an integer, return its negation, '
        'otherwise fail"',
        "requires int",
    ),
    RejectCase(
        "unary_not_on_int",
        "not 5;",
        'Unary "not E": "if the value of E is a boolean, return its negation, '
        'otherwise fail"',
        "requires bool",
    ),
    RejectCase(
        "equality_type_mismatch",
        "1 == true;",
        "Implementation-defined: == is statically restricted to operands of "
        "the same type",
        "requires two of the same type",
    ),
    RejectCase(
        "arithmetic_on_non_int",
        "true + 1;",
        "Implementation-defined: arithmetic operators are statically restricted "
        "to Int operands",
        "requires two integers",
    ),
    RejectCase(
        "and_on_non_bool",
        "1 and true;",
        "Implementation-defined: and/or are statically restricted to Bool "
        "operands (spec's dynamic semantics for and/or don't state a fail "
        "case explicitly)",
        "requires two Bools",
    ),
    RejectCase(
        "print_int_with_bool_arg",
        "print_int(true);",
        'Built-in print_int: "prints an integer" — implementation-defined '
        "static argument-type check",
        "print_int expects argument of type Int",
    ),
    RejectCase(
        "print_bool_with_int_arg",
        "print_bool(5);",
        'Built-in print_bool: "prints either true or false" — implementation-'
        "defined static argument-type check",
        "print_bool expects argument of type Bool",
    ),
    RejectCase(
        "typed_var_decl_type_mismatch",
        "var x: Bool = 5;",
        "Typed variable declaration: declared type T must match the "
        "initializer's type (implementation-defined static rule)",
        "expected Bool, got Int",
    ),
    RejectCase(
        "var_decl_initializer_undeclared_identifier",
        "var x = y;",
        'Variable declaration initializer uses lookup: "fail if not found"',
        "Unknown identifier",
    ),
    RejectCase(
        "var_decl_initializer_unit_block",
        "var x = { var y = 1; };",
        "Implementation-defined: a Unit-valued block (one ending in `;`, with no "
        "result expression) can't be used as a variable initializer — not a spec "
        "rule, but a restriction both ir_generator.py and type_checker.py enforce",
        "Block needs a result expression",
    ),
    RejectCase(
        "if_condition_non_bool",
        "if 1 then print_int(1);",
        'If-then conditional: "if the value of E1 is neither true nor false, fail". '
        "Previously caught by parser.py at parse time; now only type_checker.py "
        "checks this (parser.py's copy was removed).",
        "if condition must be Bool",
    ),
    RejectCase(
        "while_condition_non_bool",
        "while 1 do { print_int(1); }",
        'While-loop: "if the value of E1 is something else, fail". Previously '
        "caught by parser.py at parse time; now only type_checker.py checks "
        "this (parser.py's copy was removed).",
        "while condition must be Bool",
    ),
    RejectCase(
        "if_else_branches_type_mismatch",
        "if true then 1 else false;",
        "Implementation-defined: if/else branches must have the same static "
        "type (spec's dynamic semantics don't require this — E2/E3 could differ "
        "at runtime since only one ever evaluates). Previously caught by "
        "parser.py at parse time; now only type_checker.py checks this "
        "(parser.py's copy was removed).",
        "if branches must have the same type",
    ),
]


@pytest.mark.parametrize("case", REJECTS, ids=[c.name for c in REJECTS])
def test_ir_generator_rejects_ill_typed_program(case: RejectCase) -> None:
    tokens = tokenize(case.source)
    parsed = parse(tokens)
    with pytest.raises(Exception, match=case.expected_message):
        generate_ir(GLOBAL_SYMTAB, parsed)
