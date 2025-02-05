import astree as ast
from datatypes import Int, Bool, Unit, Type, FunType
from typing import Optional
from dataclasses import dataclass


@dataclass
class TypeSymTab:
    locals: dict[str, Type]
    parent: Optional["TypeSymTab"] = None

    def lookup(self, name: str) -> Type:
        if name in self.locals:
            return self.locals[name]
        if self.parent is not None:
            return self.parent.lookup(name)
        raise TypeError(f"Unbound variable {name}")


built_in_types = TypeSymTab({
    "+": FunType([Int, Int], Int),
    "-": FunType([Int, Int], Int),
    "*": FunType([Int, Int], Int),
    "/": FunType([Int, Int], Int),
    "%": FunType([Int, Int], Int),
    "and": FunType([Bool, Bool], Bool),
    "or": FunType([Bool, Bool], Bool),
    "<": FunType([Int, Int], Bool),
    ">": FunType([Int, Int], Bool),
    "<=": FunType([Int, Int], Bool),
    ">=": FunType([Int, Int], Bool),
    "print_int": FunType([Int], Unit),
    "print_bool": FunType([Bool], Unit),
    "read_int": FunType([Int], Unit),
})


def typecheck(node: ast.Expression, sym_tab: TypeSymTab) -> Type:
    match node:
        case ast.Literal(value):
            if isinstance(value, int):
                return Int
            elif isinstance(value, bool):
                return Bool
            else:
                raise TypeError(f"Unsupported literal type: {type(value)}")
        case ast.BinaryOp(left, op, right):
            if op == "==" or op == "!=":
                t1 = typecheck(left, sym_tab)
                t2 = typecheck(right, sym_tab)
                if t1 != t2:
                    raise TypeError(f"{op} requires two operands of the same type, received {t1} and {t2}")
                node.type = t1
                return node.type
            elif op not in built_in_types:
                raise TypeError(f"Unknown operator {op}")
            func_type = built_in_types.locals[op]
            t1 = typecheck(left, sym_tab)
            t2 = typecheck(right, sym_tab)
            if [t1, t2] != func_type.param_types:
                raise TypeError(f"Operator {op} expects {func_type.param_types}, got {t1} and {t2}")
            node.type = func_type.return_type
            return node.type
        case ast.Call(function, arguments):
            func_type = typecheck(function, sym_tab)
            if not isinstance(func_type, FunType):
                raise TypeError(f"{function} is not callable, got {func_type}")
            arg_types = [typecheck(arg, sym_tab) for arg in arguments]
            if arg_types != func_type.param_types:
                raise TypeError(f"Function expects {func_type.param_types}, got {arg_types}")
            node.type = func_type.return_type
            return node.type
        case ast.Identifier(name):
            node.type = sym_tab.lookup(name)
            return node.type
        case ast.VarDecl(name, initializer, datatype):
            init_type = typecheck(initializer, sym_tab)
            if name in sym_tab.locals:
                raise TypeError(f"Variable {name} already declared")
            if datatype is not None:
                if datatype != init_type:
                    raise TypeError(f"Variable {name} expects {datatype}, got {init_type}")
            sym_tab.locals[name] = init_type
            node.type = Unit
            return node.type
        case ast.UnaryOp(op, expr):
            op_type = typecheck(expr, sym_tab)
            if op == "-":
                if op_type != Int:
                    raise TypeError(f"Unary '-' expects Int, got {op_type}")
                node.type = Int
                return node.type
            elif op == "not":
                if op_type != Bool:
                    raise TypeError(f"Unary 'not' expects Bool, got {op_type}")
                node.type = Bool
                return node.type
            else:
                raise TypeError(f"Unknown unary operator {op}")
        case ast.Block(statements, result_expr):
            new_sym_tab = TypeSymTab({}, sym_tab)
            result_type = Unit
            for statement in statements:
                result_type = typecheck(statement, new_sym_tab)
            node.type = result_type
            return node.type
        case ast.IfExpr(condition, then_expr, else_expr):
            cond_type = typecheck(condition, sym_tab)
            if cond_type != Bool:
                raise TypeError(f"If condition must be Bool, got {cond_type}")
            then_type = typecheck(then_expr, sym_tab)
            if else_expr is not None:
                else_type = typecheck(else_expr, sym_tab)
                if then_type != else_type:
                    raise TypeError(f"If branches must have the same type, got {then_type} and {else_type}")
                node.type = then_expr
            else:
                node.type = Unit
            return node.type
        case ast.While(condition, statements):
            cond_type = typecheck(condition, sym_tab)
            if cond_type != Bool:
                raise TypeError(f"If condition must be Bool, got {cond_type}")
            for statement in statements:
                typecheck(statement, sym_tab)
            node.type = Unit
            return node.type
        case _:
            raise TypeError(f"Unsupported AST node {node}")
