from dataclasses import dataclass, field
from typing import Optional

import astree as ast
from datatypes import BoolType, IntType, Type, UnitType
from tokenizer import Location

BUILTIN_FUNCTIONS: dict[str, tuple[list[Type], Type]] = {
    "print_int": ([IntType()], UnitType()),
    "print_bool": ([BoolType()], UnitType()),
    "read_int": ([], IntType()),
}


@dataclass
class Binding:
    """One `var` declaration observed while type-checking: its name, resolved
    type, source location, and scope nesting depth (0 = top level). Collected
    purely for introspection/display (see check_and_collect_bindings below) —
    type_check() itself only cares whether checking succeeds.
    """
    name: str
    type: Type
    location: Location
    depth: int


@dataclass
class TypeEnv:
    vars: dict[str, Type] = field(default_factory=dict)
    parent: Optional["TypeEnv"] = None
    bindings: list[Binding] = field(default_factory=list)
    depth: int = 0

    def child(self) -> "TypeEnv":
        return TypeEnv({}, self, self.bindings, self.depth + 1)

    def lookup(self, name: str) -> Type | None:
        if name in self.vars:
            return self.vars[name]
        elif self.parent is not None:
            return self.parent.lookup(name)
        else:
            return None

    def lookup_local(self, name: str) -> Type | None:
        return self.vars.get(name)

    def declare(self, name: str, t: Type, location: Location) -> None:
        self.vars[name] = t
        self.bindings.append(Binding(name, t, location, self.depth))


def infer_block(block: ast.Block, env: TypeEnv) -> tuple[Type, TypeEnv]:
    """Type-check a block's statements in a child scope and return its result type
    along with that child scope (the latter is needed by the Program case below,
    to resolve a trailing bare identifier that's only in scope inside the block —
    mirrors the `final_expression`/`block_sym_tab` plumbing in ir_generator.py).
    """
    child_env = env.child()
    if block.result_expr is not None:
        for stmt in block.statements[:-1]:
            infer(stmt, child_env)
        result_type = infer(block.result_expr, child_env)
    else:
        for stmt in block.statements:
            infer(stmt, child_env)
        result_type = UnitType()
    return result_type, child_env


def infer(expr: ast.Expression, env: TypeEnv) -> Type:
    loc = expr.location
    match expr:
        case ast.Literal(value=value):
            match value:
                case bool():
                    return BoolType()
                case int():
                    return IntType()
                case None:
                    return UnitType()
                case _:
                    raise Exception(f"{loc}: unsupported literal: {value}")
        case ast.Identifier(name=name):
            found = env.lookup(name)
            if found is None:
                raise Exception(f"{loc}: Unknown identifier {name}")
            return found
        case ast.BinaryOp(left=left, op=op, right=right):
            if op == "=":
                if isinstance(left, ast.Identifier):
                    target_type = env.lookup(left.name)
                    if target_type is None:
                        raise Exception(
                            f"{loc}: Unknown identifier {left.name}")
                    value_type = infer(right, env)
                    if value_type != target_type:
                        raise Exception(
                            f"{loc}: assigning to {left.name} expects {target_type}, got {value_type}")
                    return target_type
                elif isinstance(left, ast.BinaryOp) and left.op == "=":
                    assert isinstance(left.right, ast.Identifier)
                    target_type = env.lookup(left.right.name)
                    if target_type is None:
                        raise Exception(
                            f"{loc}: Undefined variable: {left.right.name}")
                    value_type = infer(right, env)
                    if value_type != target_type:
                        raise Exception(
                            f"{loc}: assigning to {left.right.name} expects {target_type}, got {value_type}")
                    return infer(left, env)
                else:
                    raise Exception(
                        f"{loc}: Left side of assignment must be a variable")
            elif op in {"and", "or"}:
                left_type = infer(left, env)
                right_type = infer(right, env)
                if left_type != BoolType() or right_type != BoolType():
                    raise Exception(
                        f"{loc}: {op} requires two Bools, got {left_type} and {right_type}")
                return BoolType()
            else:
                left_type = infer(left, env)
                right_type = infer(right, env)
                if op in {"==", "!="}:
                    if left_type != right_type:
                        raise Exception(
                            f"{loc}: {op} requires two of the same type, got {left_type} and {right_type}")
                    return BoolType()
                elif op in {"+", "-", "*", "/", "%"}:
                    if left_type != IntType() or right_type != IntType():
                        raise Exception(
                            f"{loc}: {op} requires two integers, got {left_type} and {right_type}")
                    return IntType()
                elif op in {"<", "<=", ">", ">="}:
                    if left_type != IntType() or right_type != IntType():
                        raise Exception(
                            f"{loc}: {op} requires two integers, got {left_type} and {right_type}")
                    return BoolType()
                else:
                    raise Exception(f"{loc}: Unknown operator {op}")
        case ast.UnaryOp(op=op, expr=operand):
            operand_type = infer(operand, env)
            if op == "-":
                if operand_type != IntType():
                    raise Exception(
                        f"{loc}: unary_- requires int, got {operand_type}")
                return IntType()
            elif op == "not":
                if operand_type != BoolType():
                    raise Exception(
                        f"{loc}: unary_not requires bool, got {operand_type}")
                return BoolType()
            else:
                raise Exception(f"{loc}: Unknown unary operator {op}")
        case ast.IfExpr(condition=condition, then_expr=then_expr, else_expr=else_expr):
            condition_type = infer(condition, env)
            if condition_type != BoolType():
                raise Exception(
                    f"{loc}: if condition must be Bool, got {condition_type}")
            then_type = infer(then_expr, env)
            if else_expr is not None:
                else_type = infer(else_expr, env)
                if then_type != else_type:
                    raise Exception(
                        f"{loc}: if branches must have the same type, got {then_type} and {else_type}")
                return then_type
            return UnitType()
        case ast.Call(function=function, arguments=arguments):
            if function == "print_var":
                if len(arguments) != 1 or not isinstance(arguments[0], ast.Identifier):
                    raise Exception(
                        f"{loc}: print_var expects a single identifier argument")
                return infer(arguments[0], env)
            if function not in BUILTIN_FUNCTIONS:
                raise Exception(f"{loc}: Unknown function {function}")
            param_types, return_type = BUILTIN_FUNCTIONS[function]
            if len(arguments) != len(param_types):
                raise Exception(
                    f"{loc}: {function} expects {len(param_types)} argument(s), got {len(arguments)}")
            for arg, expected in zip(arguments, param_types):
                actual = infer(arg, env)
                if actual != expected:
                    raise Exception(
                        f"{loc}: {function} expects argument of type {expected}, got {actual}")
            return return_type
        case ast.Block():
            result_type, _ = infer_block(expr, env)
            return result_type
        case ast.VarDecl(name=name, initializer=initializer, type=declared_type):
            if isinstance(initializer, ast.Block) and initializer.result_expr is None:
                raise Exception(
                    f"{loc}: Block needs a result expression to be equal to variable")
            initializer_type = infer(initializer, env)
            if not isinstance(declared_type, UnitType) and declared_type != initializer_type:
                raise Exception(
                    f"{loc}: expected {declared_type}, got {initializer_type}")
            if env.lookup_local(name) is not None:
                raise Exception(
                    f"{loc}: Variable {name} already declared in this scope")
            env.declare(name, initializer_type, loc)
            return UnitType()
        case ast.While(condition=condition, statements=statements):
            condition_type = infer(condition, env)
            if condition_type != BoolType():
                raise Exception(
                    f"{loc}: while condition must be Bool, got {condition_type}")
            for stmt in statements:
                infer(stmt, env)
            return UnitType()
        case ast.Program(statements=statements, result=result):
            if result is not None:
                assert isinstance(result, ast.Call)
                for stmt in statements[:-1]:
                    infer(stmt, env)
                last = statements[-1] if statements else None
                result_env = env
                if isinstance(last, ast.Block):
                    _, result_env = infer_block(last, env)
                if result.function == "print_var":
                    target = result.arguments[0]
                    assert isinstance(target, ast.Identifier)
                    infer(target, result_env)
                else:
                    infer(result, result_env)
            else:
                for stmt in statements:
                    infer(stmt, env)
            return UnitType()
        case _:
            raise Exception(f"{loc}: Unknown AST node type: {expr}")


def check_and_collect_bindings(program: ast.Expression) -> list[Binding]:
    """Same checking as type_check(), but also returns every `var` binding
    observed along the way (declaration order), for callers that want to
    display them rather than just knowing the program is well-typed — used by
    the frontend's "Types" panel.
    """
    env = TypeEnv({})
    infer(program, env)
    return env.bindings


def type_check(program: ast.Expression) -> None:
    check_and_collect_bindings(program)
