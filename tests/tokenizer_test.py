from tokenizer import Location, Token, tokenize


def test_empty_source_produces_no_tokens() -> None:
    assert tokenize("") == []


def test_integer_and_identifier_tokens() -> None:
    assert tokenize("x1 42") == [
        Token(text="x1", type="identifier", location=Location(1, 1)),
        Token(text="42", type="int_literal", location=Location(1, 4)),
    ]


def test_keywords_are_tokenized_as_identifiers() -> None:
    # The grammar has no reserved-word token type: `var`, `if`, `then`, `while`,
    # `do`, `and`, `or`, `not` all come through as plain identifiers, and the
    # parser tells them apart from real identifiers by their text.
    for keyword in ["var", "if", "then", "else", "while", "do", "and", "or", "not"]:
        tokens = tokenize(keyword)
        assert len(tokens) == 1
        assert tokens[0].type == "identifier"
        assert tokens[0].text == keyword


def test_boolean_literals_are_tokenized_as_int_literal_type() -> None:
    # Quirk of this tokenizer: `true`/`false` get type "int_literal" rather than
    # their own literal type. The parser is what turns them into BoolType.
    tokens = tokenize("true false")
    assert [t.type for t in tokens] == ["int_literal", "int_literal"]
    assert [t.text for t in tokens] == ["true", "false"]


def test_operators() -> None:
    source = "+ - * / % == != <= >= < > ="
    tokens = tokenize(source)
    assert [t.text for t in tokens] == ["+", "-", "*",
                                        "/", "%", "==", "!=", "<=", ">=", "<", ">", "="]
    assert all(t.type == "operator" for t in tokens)


def test_punctuation() -> None:
    tokens = tokenize("(){};,")
    assert [t.text for t in tokens] == ["(", ")", "{", "}", ";", ","]
    assert all(t.type == "punctuation" for t in tokens)


def test_negative_number_is_minus_followed_by_int_literal() -> None:
    # Per the language spec, negative literals are not their own token: `-5` is
    # the operator `-` immediately followed by the int_literal `5`.
    tokens = tokenize("-5")
    assert len(tokens) == 2
    assert (tokens[0].text, tokens[0].type) == ("-", "operator")
    assert (tokens[1].text, tokens[1].type) == ("5", "int_literal")


def test_line_and_column_locations() -> None:
    tokens = tokenize("x\n  y")
    assert tokens[0].location == Location(line=1, column=1)
    assert tokens[1].location == Location(line=2, column=3)


def test_double_slash_comment_is_stripped() -> None:
    tokens = tokenize("x // this is a comment\ny")
    assert [t.text for t in tokens] == ["x", "y"]


def test_hash_comment_is_stripped() -> None:
    tokens = tokenize("x # this is a comment\ny")
    assert [t.text for t in tokens] == ["x", "y"]


def test_extra_whitespace_does_not_change_token_text_or_type() -> None:
    # Locations naturally differ (columns shift with the extra whitespace), so
    # compare text/type only, not full token equality.
    tight = [(t.text, t.type) for t in tokenize("1+2")]
    spaced = [(t.text, t.type) for t in tokenize("1  +   2")]
    assert tight == spaced
