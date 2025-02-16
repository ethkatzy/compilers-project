from dataclasses import dataclass, field
from tokenizer import Location
from datatypes import Type, IntType, BoolType, UnitType


@dataclass
class Expression:
    """Base class for AST nodes representing expressions."""
    location: Location
    type: Type = field(kw_only=True, default=UnitType)


@dataclass
class Literal(Expression):
    value: int | bool | None


@dataclass
class Identifier(Expression):
    name: str


@dataclass
class BinaryOp(Expression):
    """AST node for a binary operation like `A + B`"""
    left: Expression
    op: str
    right: Expression


@dataclass
class IfExpr(Expression):
    condition: Expression
    then_expr: Expression
    else_expr: Expression | None = None

    def __repr__(self):
        if self.else_expr:
            return f"IfExpr(condition={self.condition}, then={self.then_expr}, else={self.else_expr})"
        else:
            return f"IfExpr(condition={self.condition}, then={self.then_expr})"


@dataclass
class Call(Expression):
    """AST node for functional calls like f(x, y + z)"""
    function: str
    arguments: list[Expression]


@dataclass
class UnaryOp(Expression):
    """AST node for a unary operation like -A or not A"""
    op: str
    expr: Expression


@dataclass
class Block(Expression):
    """AST node for a block of expressions inside {}"""
    statements: list[Expression]
    result_expr: Expression


@dataclass
class VarDecl(Expression):
    """AST node for variable declarations (var x = expr)"""
    name: str
    initializer: Expression
    datatype: IntType | BoolType | UnitType | None = None


@dataclass
class Program(Expression):
    statements: list[Expression]
    result: Expression | None = None


@dataclass
class While(Expression):
    condition: Expression
    statements: list[Expression]
