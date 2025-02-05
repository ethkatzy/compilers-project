from typing import Any, Optional
import astree as ast
from parser import parser
from dataclasses import dataclass

type Value = int | bool | ast.Call | None


@dataclass
class SymTab:
    locals: dict[ast.Identifier: ast.Literal]
    parent: Optional["SymTab"] = None

    def lookup(self, name: str) -> Any:
        if name in self.locals:
            return self.locals[name]
        elif self.parent is not None:
            return self.parent.lookup(name)
        else:
            raise NameError(f"Undefined symbol: {name}")

    def assign(self, name: str, value: Any) -> None:
        if name in self.locals:
            self.locals[name] = value
        elif self.parent is not None:
            self.parent.assign(name, value)
        else:
            raise NameError(f"Undefined variable: {name}")


GLOBAL_SYMBOLS = SymTab(locals={
    "or": lambda a, b: a or b,
    "and": lambda a, b: a and b,
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    "<": lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
    ">": lambda a, b: a > b,
    ">=": lambda a, b: a > b,
    "+": lambda a, b: a + b,
    "-": lambda a, b: a - b,
    "*": lambda a, b: a * b,
    "/": lambda a, b: a / b,
    "%": lambda a, b: a % b,
    "not": lambda a: not a,
    "unary_neg": lambda a: -a,
})


def interpret(node: ast.Expression, sym_tab: SymTab) -> Value:
    match node:
        case ast.Literal(value):
            return value
        case ast.Identifier(name):
            return sym_tab.lookup(name)
        case ast.BinaryOp(left, op, right):
            a = interpret(left, sym_tab)
            if op == "and":
                return a and interpret(right, sym_tab) if bool(a) else False
            elif op == "or":
                return a or interpret(right, sym_tab) if bool(a) else True
            else:
                b: Any = interpret(right, sym_tab)
                if op == "=":
                    sym_tab.assign(left.name, b)
                    return None
                op_func = sym_tab.lookup(op)
                return op_func(a, b)
        case ast.UnaryOp(op, expr):
            a: Any = interpret(expr, sym_tab)
            if op == "-":
                op_func = sym_tab.lookup("unary_neg")
                return op_func(a)
            op_func = sym_tab.lookup(op)
            return op_func(a)
        case ast.IfExpr(condition, then_expr, else_expr):
            if interpret(condition, sym_tab):
                return interpret(then_expr, sym_tab)
            else:
                return interpret(else_expr, sym_tab)
        case ast.Program(statements):
            result = None
            for statement in statements:
                result = interpret(statement, sym_tab)
            return result
        case ast.Block(statements):
            new_sym_tab = SymTab(locals={}, parent=sym_tab)
            result = None
            for statement in statements:
                result = interpret(statement, new_sym_tab)
            return result
        case ast.VarDecl(name, initializer):
            value = interpret(initializer, sym_tab)
            if name in sym_tab.locals:
                raise NameError(f"Variable {name} already declared")
            sym_tab.locals[name] = value
            return value
        case ast.Call(function, arguments):
            if function[:5] == "print":
                if isinstance(arguments[0], ast.Identifier):
                    value = interpret(arguments[0], sym_tab)
                else:
                    value = arguments[0].value
            if function == "print_int":
                try:
                    print(int(value))
                except TypeError:
                    raise TypeError(f"print_int only prints integers")
            elif function == "print_bool":
                try:
                    print(bool(value))
                except TypeError:
                    raise TypeError(f"print_bool only prints bools")
            elif function == "read_int":
                try:
                    return int(input())
                except TypeError:
                    raise TypeError(f"read_int only reads integers")
            else:
                raise Exception(f"Unexpected function: {function}")
        case ast.While(condition, statements):
            result = None
            while interpret(condition, sym_tab):
                for statement in statements:
                    result = interpret(statement, sym_tab)
            return result
        case _:
            raise Exception(f"Unknown type: {type(node)}")


parsed = parser("""
var x = 0;
while x < 3 do {
x = x + 1;
print_int(x)}
""")
global_sym_tab = SymTab({}, GLOBAL_SYMBOLS)
print(interpret(parsed, global_sym_tab))
