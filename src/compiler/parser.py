from tokenizer import Token, tokenize, Location
import astree as ast
from datatypes import IntType, BoolType, UnitType


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
        if token.text == "true":
            return ast.Literal(token.location, True, type=BoolType())
        elif token.text == "false":
            return ast.Literal(token.location, False, type=BoolType())
        else:
            return ast.Literal(token.location, int(token.text), type=IntType())

    def parse_identifier() -> ast.Identifier:
        if peek().type != "identifier":
            raise Exception(f"{peek().location}: expected an identifier")
        token = consume()
        return ast.Identifier(token.location, token.text)

    def parse_if_expression() -> ast.Expression:
        token = consume("if")
        condition = parse_expression()
        if not isinstance(condition.type, BoolType):
            raise Exception(f"{token.location}: expected a boolean type for if condition, got {condition.type}")
        consume("then")
        then_expr = parse_expression()
        else_expr = None
        if peek().text == "else":
            consume("else")
            else_expr = parse_expression()
            if then_expr.type != else_expr.type:
                raise Exception(f"{then_expr.location}: if-clause branches must have the same type, got {then_expr.type} and {else_expr.type}")
            return ast.IfExpr(token.location, condition, then_expr, else_expr, type=then_expr.type)
        else:
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
                left = ast.BinaryOp(token.location, left, op, right, type=BoolType())
            elif op in {"and"} and precedence < 3:
                token = consume("and")
                right = parse_expression(3)
                left = ast.BinaryOp(token.location, left, op, right, type=BoolType())
            elif op in {"==", "!="} and precedence < 4:
                token = consume(op)
                right = parse_expression(4)
                left = ast.BinaryOp(token.location, left, op, right, type=BoolType())
            elif op in {"<", "<=", ">", ">="} and precedence < 4:
                token = consume(op)
                right = parse_expression(4)
                left = ast.BinaryOp(token.location, left, op, right, type=BoolType())
            elif op in {"+", "-"} and precedence < 5:
                token = consume(op)
                right = parse_expression(5)
                left = ast.BinaryOp(token.location, left, op, right, type=IntType())
            elif op in {"*", "/", "%"} and precedence < 6:
                token = consume(op)
                right = parse_expression(6)
                left = ast.BinaryOp(token.location, left, op, right, type=IntType())
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
        if not isinstance(condition.type, BoolType):
            raise Exception(f"{token.location}: expected a boolean for while condition, got {condition.type}")
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
        final_semi_colon = False if prev().text != ";" else True
        consume("}")
        result_expr = final_statement(statements[-1], False) if (not final_semi_colon and statements) else None
        return ast.Block(token.location, statements, result_expr)

    def final_statement(stmt: ast.Expression, final_flag: bool) -> ast.Expression | None:
        loc = stmt.location
        match stmt:
            case ast.Literal(type=type):
                if isinstance(type, IntType):
                    return ast.Call(loc, "print_int", [stmt]) if final_flag else stmt
                elif isinstance(type, BoolType):
                    return ast.Call(loc, "print_bool", [stmt]) if final_flag else stmt
                else:
                    return None
            case ast.Identifier():
                return ast.Call(loc, "print_var", [stmt]) if final_flag else stmt
            case ast.BinaryOp(type=type, right=right):
                if isinstance(type, IntType):
                    return ast.Call(loc, "print_int", [stmt]) if final_flag else stmt
                elif isinstance(type, BoolType):
                    return ast.Call(loc, "print_bool", [stmt]) if final_flag else stmt
                else:
                    return final_statement(right, True) if final_flag else right
            case ast.IfExpr(else_expr=else_expr, type=type):
                if else_expr is None:
                    return None
                else:
                    if isinstance(type, IntType):
                        return ast.Call(loc, "print_int", [stmt]) if final_flag else stmt
                    elif isinstance(type, BoolType):
                        return ast.Call(loc, "print_bool", [stmt]) if final_flag else stmt
            case ast.Call(function=function):
                if function == "read_int":
                    return ast.Call(loc, "print_int", [stmt]) if final_flag else stmt
                else:
                    return None
            case ast.UnaryOp(type=type):
                if isinstance(type, IntType):
                    return ast.Call(loc, "print_int", [stmt]) if final_flag else stmt
                else:
                    return ast.Call(loc, "print_bool", [stmt]) if final_flag else stmt
            case ast.Block(result_expr=result_expr):
                if result_expr is not None:
                    return final_statement(result_expr, final_flag)
                else:
                    return None
            case ast.VarDecl():
                return None
            case ast.While():
                return None
            case _:
                raise Exception(f"{stmt.location}: Unknown AST node {stmt}")

    def parse_unary_op(op: str) -> ast.UnaryOp:
        token = consume(op)
        expr = parse_expression(8)
        if op == "-":
            return ast.UnaryOp(token.location, op, expr, type=IntType())
        elif op == "not":
            return ast.UnaryOp(token.location, op, expr, type=BoolType())
        else:
            raise Exception(f"{peek().location}: Unknown unary operator, expected 'not' or '{op}'")

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
            return ast.VarDecl(token.location, name, initializer, type=initializer.type)
        elif peek().text in {"Int, Bool", "Unit"}:
            datatype = peek().text
            consume(datatype)
            if peek().text != "=":
                raise Exception(f"{peek().location}: expected '=' after variable")
            consume("=")
            initializer = parse_expression()
            if datatype == "Int":
                return ast.VarDecl(token.location, name, initializer, type=IntType())
            elif datatype == "Bool":
                return ast.VarDecl(token.location, name, initializer, type=BoolType())
            else:
                return ast.VarDecl(token.location, name, initializer, type=UnitType())
        else:
            raise Exception(f"{peek().location}: Expected data type or = after variable")

    def parse_program() -> ast.Program:
        expressions = []
        while peek().type != "end":
            expr = parse_expression(allowVarDecl=True)
            expressions.append(expr)
            if prev().text == "}":
                if peek().text == ";":
                    consume(";")
            elif peek().text == ";":
                consume(";")
            elif peek().type != "end":
                raise Exception(f"{peek().location}: expected ';'")
        location = Location(0, 0)
        if prev().text != ";":
            final_expr = final_statement(expressions[-1], True)
            return ast.Program(location, expressions, final_expr)
        return ast.Program(location, expressions)

    result = parse_program()
    if pos < len(tokens):
        raise Exception(f"{tokens[pos].location}: Unexpected token '{tokens[pos].text}' at the end of input")

    return result


def parser(code: str) -> ast.Expression:
    tokens = tokenize(code)
    return parse(tokens)


#print(parser("""2 + 2;"""))
