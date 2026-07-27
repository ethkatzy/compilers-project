import pytest
from parser import parse
from tokenizer import tokenize
from type_checker import type_check

from .test_pipeline import PROGRAMS, ProgramCase
from .type_checker_baseline_test import REJECTS, RejectCase


@pytest.mark.parametrize("case", PROGRAMS, ids=[c.name for c in PROGRAMS])
def test_type_checker_accepts_valid_programs(case: ProgramCase) -> None:
    tokens = tokenize(case.source)
    parsed = parse(tokens)
    type_check(parsed)


@pytest.mark.parametrize("case", REJECTS, ids=[c.name for c in REJECTS])
def test_type_checker_rejects_ill_typed_programs(case: RejectCase) -> None:
    """parser.py no longer does any type checking of its own (if/while condition
    types and if/else branch type matches used to be checked there too), so
    every REJECTS case is now exercised purely by type_check() — parsing always
    succeeds first, and type_check() is what raises.
    """
    tokens = tokenize(case.source)
    parsed = parse(tokens)
    with pytest.raises(Exception, match=case.expected_message):
        type_check(parsed)


PARSER_FORMERLY_CHECKED = [c for c in REJECTS if c.name in {
    "if_condition_non_bool",
    "while_condition_non_bool",
    "if_else_branches_type_mismatch",
}]


@pytest.mark.parametrize("case", PARSER_FORMERLY_CHECKED, ids=[c.name for c in PARSER_FORMERLY_CHECKED])
def test_responsibility_moved_from_parser_to_type_checker(case: RejectCase) -> None:
    """These three rules used to be checked inline in parser.py (raising during
    parse()). Now parser.py does no type checking at all, so parsing these
    ill-typed programs must succeed, and type_check() must be what rejects them.
    """
    tokens = tokenize(case.source)
    parsed = parse(tokens)  # must not raise: parser.py no longer checks types
    with pytest.raises(Exception, match=case.expected_message):
        type_check(parsed)
