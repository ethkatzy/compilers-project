from tokenizer import Token, tokenize, Location
import astree as ast


def parse(tokens: list[Token]) -> ast.Expression:
    if not tokens:
        raise Exception("Error: Empty input, no tokens to parse")
    pos = 0

    def peek() -> Token:
        if pos < len(tokens):
            return tokens[pos]
        else:
            return Token(
                location=tokens[-1].location,
                type="end",
                text="",
            )

    def prev() -> Token:
        if pos != 0:
            return tokens[pos - 1]

    def consume(expected: str | list[str] | None = None) -> Token:
        nonlocal pos
        token = peek()
        if isinstance(expected, str) and token.text != expected:
            raise Exception(f"{token.location}: expected '{expected}'")
        if isinstance(expected, list) and token.text not in expected:
            comma_separated = ", ".join(f'"{e}"' for e in expected)
            raise Exception(f"{token.location}: expected one of: '{comma_separated}'")
        pos += 1
        return token

    def parse_int_literal() -> ast.Literal:
        if peek().type != "int_literal":
            raise Exception(f"{peek().location}: expected an integer literal")
        token = consume()
        if token.text == "True":
            return ast.Literal(token.location, True)
        elif token.text == "False":
            return ast.Literal(token.location, False)
        else:
            return ast.Literal(token.location, int(token.text))

    def parse_identifier() -> ast.Identifier:
        if peek().type != "identifier":
            raise Exception(f"{peek().location}: expected an identifier")
        token = consume()
        return ast.Identifier(token.location, token.text)

    def parse_if_expression() -> ast.Expression:
        token = consume("if")
        condition = parse_expression()
        consume("then")
        then_expr = parse_expression()
        else_expr = None
        if peek().text == "else":
            consume("else")
            else_expr = parse_expression()
        return ast.IfExpr(token.location, condition, then_expr, else_expr)

    def parse_expression(precedence: int = 0, allowVarDecl: bool = False) -> ast.Expression:
        """Parse expressions based on operator precedence."""
        if allowVarDecl and peek().text == "var":
            return parse_var_decl()
        left = parse_primary()
        while True:
            op = peek().text
            if op == "=" and precedence < 1:
                token = consume("=")
                right = parse_expression(1)
                left = ast.BinaryOp(token.location, left, op, right)
            elif op in {"or"} and precedence < 2:
                token = consume("or")
                right = parse_expression(2)
                left = ast.BinaryOp(token.location, left, op, right)
            elif op in {"and"} and precedence < 3:
                token = consume("and")
                right = parse_expression(3)
                left = ast.BinaryOp(token.location, left, op, right)
            elif op in {"==", "!=", "<", "<=", ">", ">="} and precedence < 4:
                token = consume(op)
                right = parse_expression(4)
                left = ast.BinaryOp(token.location, left, op, right)
            elif op in {"+", "-"} and precedence < 5:
                token = consume(op)
                right = parse_expression(5)
                left = ast.BinaryOp(token.location, left, op, right)
            elif op in {"*", "/", "%"} and precedence < 6:
                token = consume(op)
                right = parse_expression(6)
                left = ast.BinaryOp(token.location, left, op, right)
            else:
                break
        return left

    def parse_primary() -> ast.Expression:
        if peek().text == "{":
            return parse_block()
        elif peek().text == "if":
            return parse_if_expression()
        elif peek().text == "while":
            return parse_while()
        elif peek().text == "(":
            return parse_parenthesized()
        elif peek().text == "not":
            return parse_unary_op("not")
        elif peek().text == "-":
            return parse_unary_op("-")
        elif peek().type == "int_literal":
            return parse_int_literal()
        elif peek().type == "identifier":
            identifier = parse_identifier()
            if peek().text == "(":
                return parse_function_call(identifier)
            return identifier
        else:
            raise Exception(f"{peek().location}: expected '(', an integer literal or an identifier")

    def parse_while() -> ast.While:
        token = consume("while")
        condition = parse_expression()
        consume("do")
        consume("{")
        statements = []
        while peek().text != "}":
            expr = parse_expression(allowVarDecl=True)
            statements.append(expr)
            if peek().text == ";":
                consume(";")
            elif peek().text != "}" and prev().text != "}":
                raise Exception(f"{peek().location}: expected ';' or '}}'")
        consume("}")
        return ast.While(token.location, condition, statements)

    def parse_block() -> ast.Block:
        token = consume("{")
        statements = []
        while peek().text != "}":
            expr = parse_expression(allowVarDecl=True)
            statements.append(expr)
            if peek().text == ";":
                consume(";")
            elif peek().text != "}" and prev().text != "}":
                raise Exception(f"{peek().location}: expected ';' or '}}'")
        consume("}")

        result_expr = statements[-1] if statements else ast.Literal(token.location, value=None)
        return ast.Block(token.location, statements, result_expr)

    def parse_unary_op(op: str) -> ast.UnaryOp:
        token = consume(op)
        expr = parse_expression(8)
        return ast.UnaryOp(token.location, op, expr)

    def parse_function_call(identifier: ast.Identifier) -> ast.Call:
        token = consume("(")
        arguments = []
        if peek().text != ")":
            while True:
                arguments.append(parse_expression())
                if peek().text == ",":
                    consume(",")
                else:
                    break
        consume(")")
        return ast.Call(token.location, identifier.name, arguments)

    def parse_parenthesized() -> ast.Expression:
        consume("(")
        expr = parse_expression()
        consume(")")
        return expr

    def parse_var_decl() -> ast.VarDecl:
        """Parse a variable declaration: var x = expr"""
        token = consume("var")
        if peek().type != "identifier":
            raise Exception(f"{peek().location}: expected an identifier after 'var'")
        name = consume().text
        if peek().text == "=":
            consume("=")
            initializer = parse_expression()
            return ast.VarDecl(token.location, name, initializer)
        elif peek().text == "Bool" or peek().text == "Int":
            datatype = peek().type
            consume(datatype)
            if peek().text != "=":
                raise Exception(f"{peek().location}: expected '=' after variable")
            consume("=")
            initializer = parse_expression()
            return ast.VarDecl(token.location, name, initializer, datatype)
        else:
            raise Exception(f"{peek().location}: Expected data type or = after variable")

    def parse_program() -> ast.Program:
        expressions = []
        while peek().type != "end":
            expr = parse_expression(allowVarDecl=True)
            expressions.append(expr)
            if peek().text == ";":
                consume(";")
            elif peek().type != "end":
                raise Exception(f"{peek().location}: expected ';'")
        location = Location(0, 0)
        return ast.Program(location, expressions)

    result = parse_program()
    if pos < len(tokens):
        raise Exception(f"{tokens[pos].location}: Unexpected token '{tokens[pos].text}' at the end of input")

    return result


def parser(code: str) -> ast.Expression:
    tokens = tokenize(code)
    return parse(tokens)
