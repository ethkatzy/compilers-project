import re
from dataclasses import dataclass


@dataclass
class Location:
    line: int
    column: int


@dataclass
class Token:
    text: str
    type: str
    location: Location


def tokenize(source_code: str) -> list[Token]:
    token_pattern = re.compile(
        r'\b[_a-zA-Z][_a-zA-Z0-9]*\b'
        r'|\b\d+\b'
        r'|==|!=|<=|>=|%|<|>|=|\+|\-|\*|/'
        r'|[(){}.,;:]'
    )
    comment_pattern = re.compile(r'//.*|#.*')
    tokens = []
    lines = source_code.split('\n')

    for lineNumber, line in enumerate(lines, start=1):
        line = comment_pattern.sub('', line)
        pos = 0
        for match in token_pattern.finditer(line):
            _check_no_stray_characters(line, pos, match.start(), lineNumber)
            text = match.group()
            column = match.start() + 1
            if text.isdigit() or text == "true" or text == "false":
                type = 'int_literal'
            elif re.fullmatch(r'[_a-zA-Z][_a-zA-Z0-9]*', text):
                type = 'identifier'
            elif text in {'+', '-', '*', '/', '%', '=', '==', '!=', '<', '<=', '>', '>='}:
                type = 'operator'
            elif text in {'(', ')', '{', '}', ',', ';', ':'}:
                type = 'punctuation'
            else:
                type = 'other'

            location = Location(lineNumber, column)
            tokens.append(Token(text, type, location))
            pos = match.end()
        _check_no_stray_characters(line, pos, len(line), lineNumber)

    return tokens


def _check_no_stray_characters(line: str, start: int, end: int, line_number: int) -> None:
    """Raises if line[start:end] (a gap between/around recognized tokens) contains
    anything but whitespace -- e.g. a stray `"`, `@`, backtick, etc. Without this,
    such characters were silently dropped instead of being rejected, which let
    nonsense like `print_int("2")` quietly tokenize as `print_int(2)`.
    """
    gap = line[start:end]
    stripped = gap.lstrip()
    if stripped:
        column = start + (len(gap) - len(stripped)) + 1
        location = Location(line_number, column)
        raise Exception(f"{location}: unexpected character {stripped[0]!r}")
