import ir
import astree as ast
from datatypes import Bool, Int, Type, Unit, IntType, BoolType
from tokenizer import Location
from parser import parser
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class SymTab:
    locals: dict[(str | None, Type), ir.IRVar]
    parent: Optional["SymTab"] = None

    def local_lookup(self, name: str, t: Type) -> Any:
        return self.locals[(name, t)] if (name, t) in self.locals else None

    def lookup(self, name: str, t: Type) -> Any:
        if (name, t) in self.locals:
            return self.locals[(name, t)]
        elif self.parent is not None:
            return self.parent.lookup(name, t)
        else:
            raise NameError(f"Undefined symbol: {name}")


def generate_ir(root_table: SymTab, root_expr: ast.Expression) -> list[ir.Instruction]:
    var_unit = ir.IRVar('unit')
    counter = 1
    ins: list[ir.Instruction] = []
    label_counter = 1

    def new_var(t: Type, st: SymTab, name: str | None = None):
        nonlocal counter
        var = ir.IRVar(f"x{counter}")
        if name is not None:
            st.locals[(name, t)] = var
        counter += 1
        return var, st

    def new_label(loc: Location) -> ir.Label:
        nonlocal label_counter
        label_name = ir.Label(loc, f"L{label_counter}")
        label_counter += 1
        return label_name

    def visit(st: SymTab, expr: ast.Expression, final_expression: bool = False) -> ir.IRVar:
        loc = expr.location
        match expr:
            case ast.Literal(value=value):
                match value:
                    case bool():
                        var, st = new_var(Bool, st)
                        ins.append(ir.LoadBoolConst(loc, value, var))
                    case int():
                        var, st = new_var(Bool, st)
                        ins.append(ir.LoadIntConst(loc, value, var))
                    case None:
                        var = var_unit
                    case _:
                        raise Exception(f"{loc}: unsupported literal: {value}")
                return var
            case ast.Identifier(name=name, type=type):
                if st.local_lookup(name, Int) is not None:
                    return st.local_lookup(name, Int)
                elif st.local_lookup(name, Bool) is not None:
                    return st.local_lookup(name, Bool)
                else:
                    raise Exception(f"{loc}: undefined variable: {name}")
            case ast.BinaryOp(left=left, op=op, right=right, type=type):
                if op == "=":
                    if not (isinstance(left, ast.BinaryOp) and left.op == "="):
                        if not isinstance(left, ast.Identifier):
                            raise Exception(f"{loc}: Left side of assignment must be a variable")
                        if st.local_lookup(left.name, Int) is not None:
                            var_left = st.local_lookup(left.name, Int)
                        elif st.local_lookup(left.name, Bool) is not None:
                            var_left = st.local_lookup(left.name, Bool)
                        else:
                            raise Exception(f"{loc}: Undefined variable: {left.name} or assigning wrong type {right.type}")
                        var_right = visit(st, right)
                        ins.append(ir.Copy(loc, var_right, var_left))
                        return var_left
                    else:
                        var_right = visit(st, right)
                        t = Unit
                        if isinstance(type, IntType):
                            t = Int
                        elif isinstance(type, BoolType):
                            t = Bool
                        ins.append(ir.Copy(loc, var_right, st.lookup(left.right.name, t)))
                        var_left = visit(st, left)
                        return var_left
                elif op in {"and", "or"}:
                    l_skip = new_label(loc)
                    l_right = new_label(loc)
                    l_end = new_label(loc)
                    var_left = visit(st, left)
                    if op == "and":
                        ins.append(ir.CondJump(loc, var_left, l_skip, l_right))
                    else:
                        ins.append(ir.CondJump(loc, var_left, l_right, l_skip))
                    ins.append(l_skip)
                    var_right = visit(st, right)
                    extra_var, st = new_var(Bool, st)
                    ins.append(ir.Copy(loc, var_right, extra_var))
                    ins.append(ir.Jump(loc, l_end))
                    ins.append(l_right)
                    if op == "and":
                        ins.append(ir.LoadBoolConst(loc, False, extra_var))
                    else:
                        ins.append(ir.LoadBoolConst(loc, True, extra_var))
                    ins.append(ir.Jump(loc, l_end))
                    ins.append(l_end)
                    return extra_var
                else:
                    t = Unit
                    if isinstance(type, IntType):
                        t = Int
                    elif isinstance(type, BoolType):
                        t = Bool
                    var_op = st.lookup(op, t)
                    var_left = visit(st, left)
                    var_right = visit(st, right)
                    var_result, st = new_var(t, st)
                    ins.append(ir.Call(loc, var_op, [var_left, var_right], var_result))
                    return var_result
            case ast.IfExpr(condition=condition, then_expr=then_expr, else_expr=else_expr, type=type):
                if else_expr is not None:
                    l_then = new_label(loc)
                    l_else = new_label(loc)
                    l_end = new_label(loc)
                    var_cond = visit(st, condition)
                    ins.append(ir.CondJump(loc, var_cond, l_then, l_else))
                    ins.append(l_then)
                    t = Unit
                    if isinstance(type, IntType):
                        t = Int
                    elif isinstance(type, BoolType):
                        t = Bool
                    var_result, st = new_var(t, st)
                    var_then = visit(st, then_expr)
                    ins.append(ir.Copy(loc, var_then, var_result))
                    ins.append(ir.Jump(loc, l_end))
                    ins.append(l_else)
                    var_else = visit(st, else_expr)
                    ins.append(ir.Copy(loc, var_else, var_result))
                    ins.append(l_end)
                    return var_result
                else:
                    l_then = new_label(loc)
                    l_end = new_label(loc)
                    var_cond = visit(st, condition)
                    ins.append(ir.CondJump(loc, var_cond, l_then, l_end))
                    ins.append(l_then)
                    var_then = visit(st, then_expr)
                    ins.append(ir.Jump(loc, l_end))
                    ins.append(l_end)
                    return var_unit
            case ast.Call(function=function, arguments=arguments):
                var_func = ir.IRVar(function)
                var_args = [visit(st, arg) for arg in arguments]
                var_result, st = new_var(Unit, st)
                ins.append(ir.Call(loc, var_func, var_args, var_result))
                return var_result
            case ast.Block(statements=statements, result_expr=result_expr):
                block_sym_tab = SymTab({}, st)
                if result_expr is not None:
                    for i in range(len(statements) - 1):
                        visit(block_sym_tab, statements[i])
                    if final_expression:
                        return var_unit
                    else:
                        var_result = visit(block_sym_tab, result_expr)
                        return var_result
                else:
                    for stmt in statements:
                        visit(block_sym_tab, stmt)
                    return var_unit
            case ast.UnaryOp(op=op, expr=expr):
                if op == "-":
                    neg = "unary_-"
                    type = Int
                    var_op = st.lookup(neg, type)
                else:
                    neg = "unary_not"
                    type = Bool
                    var_op = st.lookup(neg, type)
                var_operand = visit(st, expr)
                var_result, st = new_var(type, st)
                ins.append(ir.Call(loc, var_op, [var_operand], var_result))
                return var_result
            case ast.VarDecl(name=name, initializer=initializer, type=type):
                t = Unit
                if isinstance(type, IntType):
                    t = Int
                elif isinstance(type, BoolType):
                    t = Bool
                else:
                    if st.local_lookup(initializer.name, Int) is not None:
                        t = Int
                    elif st.local_lookup(initializer.name, Bool) is not None:
                        t = Bool
                if st.local_lookup(name, t) is None:
                    var_value = visit(st, initializer)
                    var_decl, st = new_var(t, st, name)
                    ins.append(ir.Copy(loc, var_value, var_decl))
                    return var_unit
                else:
                    raise Exception(f"{loc}: Variable {name} already declared in this scope")
            case ast.While(condition=condition, statements=statements):
                l_cond = new_label(loc)
                l_body = new_label(loc)
                l_end = new_label(loc)
                ins.append(l_cond)
                var_cond = visit(st, condition)
                ins.append(ir.CondJump(loc, var_cond, l_body, l_end))
                ins.append(l_body)
                for stmt in statements:
                    visit(st, stmt)
                ins.append(ir.Jump(loc, l_cond))
                ins.append(l_end)
                return var_unit
            case ast.Program(location=location, statements=statements, result=result):
                if result is not None:
                    for i in range(len(statements) - 1):
                        visit(st, statements[i])
                    if isinstance(statements[-1], ast.Block):
                        visit(st, statements[-1], True)
                    if result.function == "print_var":
                        if st.local_lookup(result.arguments[0].name, Int) is not None:
                            visit(st, ast.Call(location, "print_int", result.arguments), True)
                        elif st.local_lookup(result.arguments[0].name, Bool) is not None:
                            visit(st, ast.Call(location, "print_bool", result.arguments), True)
                    else:
                        visit(st, result, True)
                else:
                    for stmt in statements:
                        visit(st, stmt)
                return var_unit
            case _:
                raise Exception(f"{loc}: Unknown AST node type: {ast}")

    new_sym_tab = SymTab({}, root_table)
    visit(new_sym_tab, root_expr)
    return ins


GLOBAL_SYMTAB = SymTab({("+", Int): ir.IRVar("+"),
                        ("-", Int): ir.IRVar("-"),
                        ("*", Int): ir.IRVar("*"),
                        ("/", Int): ir.IRVar("/"),
                        ("%", Int): ir.IRVar("%"),
                        ("<", Bool): ir.IRVar("<"),
                        ("<=", Bool): ir.IRVar("<="),
                        ("==", Bool): ir.IRVar("=="),
                        (">=", Bool): ir.IRVar(">="),
                        (">", Bool): ir.IRVar(">"),
                        ("!=", Bool): ir.IRVar("!="),
                        ("unary_-", Int): ir.IRVar("unary_-"),
                        ("unary_not", Bool): ir.IRVar("unary_not"),
                        ("print_int", Unit): ir.IRVar("print_int"),
                        ("print_bool", Unit): ir.IRVar("print_bool"),
                        ("read_int", Unit): ir.IRVar("read_int"),
                        })

#string = """var x = 3;
#var y = x;
#x = 4;
#y"""
#tokens = parser(string)
#ir_lines = generate_ir(GLOBAL_SYMTAB, tokens)
#for line in ir_lines:
#    print(line)
