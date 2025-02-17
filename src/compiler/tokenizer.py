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
        r'|[(){}.,;]'
    )
    comment_pattern = re.compile(r'//.*|#.*')
    tokens = []
    lines = source_code.split('\n')

    for lineNumber, line in enumerate(lines, start=1):
        line = comment_pattern.sub('', line)
        for match in token_pattern.finditer(line):
            text = match.group()
            column = match.start() + 1
            if text.isdigit() or text == "true" or text == "false":
                type = 'int_literal'
            elif re.fullmatch(r'[_a-zA-Z][_a-zA-Z0-9]*', text):
                type = 'identifier'
            elif text in {'+', '-', '*', '/', '%', '=', '==', '!=', '<', '<=', '>', '>='}:
                type = 'operator'
            elif text in {'(', ')', '{', '}', ',', ';'}:
                type = 'punctuation'
            else:
                type = 'other'

            location = Location(lineNumber, column)
            tokens.append(Token(text, type, location))

    return tokens
