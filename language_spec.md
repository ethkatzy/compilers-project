# Language spec

## Example

The language looks like this:

```
var n: Int = read_int();
print_int(n);
while n > 1 do {
    if n % 2 == 0 then {
        n = n / 2;
    } else {
        n = 3*n + 1;
    }
    print_int(n);
}
```

## Syntax

This specifies the structure of a syntactically valid program in our language.
In other words, this specifies how the parser should work.

An **expression** is defined recursively as follows, where `E`, `E1`, `E2`, … `En` represent
some other arbitrary expression.

- Integer literal: a positive whole number.
  - Negative numbers should be composed of token `-` followed by an integer literal token.
- Boolean literal: either `true` or `false`.
- Identifier: a word consisting of letters, underscores or digits, but the first character must not be a digit.
- Unary operator: either `-E` or `not E`.
- Binary operator: `E1 op E2` where `op` is one of the following: `+`, `-`, `*`, `/`, `%`, `==`, `!=`, `<`, `<=`,
  `>`, `>=`, `and`, `or`, `=`.
  - Operator `=` is right-associative.
  - All other operators are left-associative.
  - Precedences are defined below.
- Parentheses: `(E)`, used to override precedence.
- Block: `{ E1; E2; ...; En }` or `{ E1; E2; ...; En; }` (may be empty, last semicolon optional).
  - Semicolons after subexpressions that end in `}` are optional.
- Untyped variable declaration: `var ID = E` where `ID` is an identifier.
- Typed variable declaration: `var ID: T = E` where `ID` is an identifier and `T` is a type expression (defined
  below).
- Conditional: `if E1 then E2` or `if E1 then E2 else E3`.
  - Nested conditionals take `E2` to be as long as possible, meaning `if a then if b then c else d` is parsed as
    `if a then (if b then c else d)`.
- While-loop: `while E1 do E2`.
- Function call: `ID(E1, E2, ..., En)` where `ID` is an identifier.

Variable declarations (`var ...`) are allowed only directly inside blocks (`{ ... }`) and in top-level
expressions.

**Type expressions** can be:

- Primitive types: `Int`, `Bool` or `Unit`.
- Function types: `(T1, T2, ...) => T` where `T1, T2, ...` (0 or more) and `T` are other type expressions.

Precedences:

1. `=`
2. `or`
3. `and`
4. `==`, `!=`
5. `<`, `<=`, `>`, `>=`
6. `+`, `-`
7. `*`, `/`, `%`
8. Unary `-` and `not`
9. All other constructs: literals, identifiers, `if`, `while`, `var`, blocks, parentheses, function calls.

All non-operator expressions such as `if`, `while` and function calls must be (syntactically) allowed to be part
of other expressions, so e.g. `1 + if true then 2 else 3` must be allowed.

The **program** consists of a single **top-level expression**. If the program text has multiple expressions
separated by semicolons, they are treated like the contents of a block, and that block becomes the top-level
expression. The last expression may be optionally followed by a semicolon.

Arbitrary amounts of whitespace are allowed between tokens. One-line comments starting with `#` or `//` are
supported.

## Semantics

This specifies how a program should work.

This works directly as a specification for an interpreter. A compiler should produce a program that behaves the
same way.

A **value** may be one of the following:

- a 64-bit signed integer (between -2<sup>63</sup> and 2<sup>63</sup> - 1)
- a boolean `true` or `false`
- a built-in function
- the special value `unit`, which means "no meaningful value"

A **context** consists of:

- **locals**: a partial map of identifiers to values
- an optional **parent context**

A **lookup** of identifier `ID` in context `C` proceeds as follows:

- if `ID` is defined in `C`'s locals, return the corresponding value
- otherwise if a lookup of `ID` in `C`'s parent succeeds, return that value
- otherwise the lookup fails

An expression is evaluated with a given context. The result of expression evaluation is a value and optionally a
modification of the context's locals.

An expression in a context `C` is evaluated as follows.

- Literal: return the constant value indicated.
- Identifier `ID`: look up `ID` from `C`, fail if not found.
- Unary operator `-E`:
  - if the value of `E` is an integer, return its negation
  - otherwise fail
- Unary operator `not E`:
  - if the value of `E` is a boolean, return its negation
  - otherwise fail
- Binary operator `E1 = E2`:
  - if `E1` is an identifier `ID`, then:
    - define context `C'` like this:
      - if `ID` is a local of `C`, define `C'` as `C`
      - otherwise define `C'` as the closest parent context of `C` that has `ID` as a local
      - if `C'` is still not defined, fail
    - set local `ID` in `C'` to the value of `E2`
  - if `E1` is not an identifier, fail
  - return the value of `E2`
- Binary operator `E1 and E2`:
  - if `E1` evaluates to false, return false and do not evaluate `E2`
  - otherwise return the value of `E2`
- Binary operator `E1 or E2`:
  - if `E1` evaluates to true, return true and do not evaluate `E2`
  - otherwise return the value of `E2`
- Other binary operators `E1 OP E2`:
  - look up the value `f` of `OP` in `C`
  - if `f` is not a function, fail
  - evaluate `E1` and then `E2`
  - call `f` with the values of `E1` and `E2` and return the result
- Block `{ E1; E2; ...; En }` or `{ E1; E2; ...; En; }`:
  - create context `C'` with no locals and parent context `C`
  - evaluate each expression `E1`, `E2`, … in context `C'`
  - if `En` is not followed by a semicolon, return the value of `En`
  - if `En` is followed by a semicolon, return `unit`
  - an empty block (`{}`) is allowed – it returns `unit`
- Variable declaration `var ID = E`:
  - if `C` already has a local `ID`, fail
  - set local `ID` in `C` to the value of `E`
  - return value `unit`
- If-then conditional `if E1 then E2`:
  - if the value of `E1` is `true`, evaluate `E2`
  - if the value of `E1` is neither `true` nor `false`, fail
  - return `unit`
- If-then-else conditional `if E1 then E2 else E3`:
  - if the value of `E1` is `true`, return the value of `E2`
  - if the value of `E1` is `false`, return the value of `E3`
  - if the value of `E1` is something else, fail
- While-loop `while E1 do E2`:
  - if the value of `E1` is true, evaluate `E2`, discard its return value, and then start evaluating the
    while-loop again
  - if the value of `E1` is false, return `unit`
  - if the value of `E1` is something else, fail
- Function call `E(E1, E2, ..., En)`:
  - let `f` be the value of `E`
  - if `f` is not a function, fail
  - evaluate each expression `E1`, `E2`, …, call `f` with their values, and return the result
  - the implementation is allowed to limit the number of allowed arguments to 6

When evaluating the top-level expression, the initial context has no parent context and has the built-in
functions and operators as its locals.

The built-in functions are:

- `print_int`: prints an integer and a newline to standard output.
- `print_bool`: prints either `true` or `false` and a newline to standard output.
- `read_int`: reads a single line, including the newline, from standard input, and interprets it as an integer.
  If the input before the newline contains characters other than digits and a prefix minus, then `read_int` is
  allowed to fail or have arbitrary behavior.

The output of a program whose evaluation succeeds consists of the outputs of any built-in print functions that
were evaluated, followed by the result of its top-level expression, if it was an integer or a boolean. (If the
top-level expression ends in a semicolon, then the result is `unit`, which is not printed.)
