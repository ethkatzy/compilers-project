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
            return None


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
        else:
            st.locals[(str(var), t)] = var
        counter += 1
        return var, st

    def new_label(loc: Location) -> ir.Label:
        nonlocal label_counter
        label_name = ir.Label(loc, f"L{label_counter}")
        label_counter += 1
        return label_name

    def visit(st: SymTab, expr: ast.Expression, final_expression: bool = False) -> ir.IRVar | SymTab:
        loc = expr.location
        match expr:
            case ast.Literal(value=value):
                match value:
                    case bool():
                        var, st = new_var(Bool, st)
                        ins.append(ir.LoadBoolConst(loc, value, var))
                    case int():
                        var, st = new_var(Int, st)
                        ins.append(ir.LoadIntConst(loc, value, var))
                    case None:
                        var = var_unit
                    case _:
                        raise Exception(f"{loc}: unsupported literal: {value}")
                return var
            case ast.Identifier(name=name, type=type):
                if st.lookup(name, Int) is not None:
                    return st.lookup(name, Int)
                elif st.lookup(name, Bool) is not None:
                    return st.lookup(name, Bool)
                else:
                    raise Exception(f"{loc}: Unknown identifier {name}")
            case ast.BinaryOp(left=left, op=op, right=right, type=type):
                if op == "=":
                    if not (isinstance(left, ast.BinaryOp) and left.op == "="):
                        if not isinstance(left, ast.Identifier):
                            raise Exception(f"{loc}: Left side of assignment must be a variable")
                        if st.lookup(left.name, Int) is not None:
                                var_left = st.lookup(left.name, Int)
                        elif st.lookup(left.name, Bool) is not None:
                            var_left = st.lookup(left.name, Bool)
                        else:
                            raise Exception(f"{loc}: Unknown identifier {left.name}")
                        var_right = visit(st, right)
                        ins.append(ir.Copy(loc, var_right, var_left))
                        return var_left
                    else:
                        var_right = visit(st, right)
                        if st.local_lookup(left.right.name, Int) is not None:
                            ins.append(ir.Copy(loc, var_right, st.local_lookup(left.right.name, Int)))
                        elif st.local_lookup(left.right.name, Bool) is not None:
                            ins.append(ir.Copy(loc, var_right, st.local_lookup(left.right.name, Bool)))
                        else:
                            raise Exception(f"{loc}: Undefined variable: {left.right.name}")
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
                    left_type = Unit
                    right_type = Unit
                    if isinstance(left, ast.Block):
                        left = left.result_expr
                    if isinstance(left, ast.Identifier) and st.local_lookup(left.name, Bool) is not None:
                        left_type = Bool
                    elif st.local_lookup(str(var_left), Bool) is not None:
                        left_type = Bool
                    elif isinstance(left, ast.Literal) and isinstance(left.type, BoolType):
                        left_type = Bool
                    if isinstance(right, ast.Block):
                        right = right.result_expr
                    if isinstance(right, ast.Identifier) and st.local_lookup(right.name, Bool) is not None:
                        right_type = Bool
                    elif st.local_lookup(str(var_right), Bool) is not None:
                        right_type = Bool
                    elif isinstance(right, ast.Literal) and isinstance(right.type, BoolType):
                        right_type = Bool
                    if not isinstance(left_type, BoolType) or not isinstance(right_type, BoolType):
                        raise Exception(f"{loc}: {op} requires two Bools, got {left_type} and {right_type}")
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
                    if var_op is None:
                        raise Exception(f"{loc}: Unknown operator {op}")
                    var_left = visit(st, left)
                    var_right = visit(st, right)
                    left_type = Unit
                    right_type = Unit
                    if isinstance(left, ast.Block):
                        left = left.result_expr
                    if isinstance(left, ast.BinaryOp):
                        if isinstance(left.type, IntType):
                            left_type = Int
                        elif isinstance(left.type, BoolType):
                            left_type = Bool
                    elif isinstance(left, ast.Identifier):
                        if st.lookup(left.name, Int) is not None:
                            left_type = Int
                        elif st.lookup(left.name, Bool) is not None:
                            left_type = Bool
                    else:
                        if st.lookup(str(var_left), Int) is not None:
                            left_type = Int
                        elif st.lookup(str(var_left), Bool) is not None:
                            left_type = Bool
                    if isinstance(right, ast.Block):
                        right = right.result_expr
                    if isinstance(right, ast.BinaryOp):
                        if isinstance(right.type, IntType):
                            right_type = Int
                        elif isinstance(right.type, BoolType):
                            right_type = Bool
                    elif isinstance(right, ast.Identifier):
                        if st.lookup(right.name, Int) is not None:
                            right_type = Int
                        elif st.lookup(right.name, Bool) is not None:
                            right_type = Bool
                    else:
                        if st.lookup(str(var_right), Int) is not None:
                            right_type = Int
                        elif st.lookup(str(var_right), Bool) is not None:
                            right_type = Bool
                    if op in {"==", "!="}:
                        if left_type != right_type:
                            raise Exception(f"{loc}: {op} requires two of the same type, got {left_type} and {right_type}")
                    elif op in {"+", "-", "*", "/", "%", "<", "<=", ">", ">="}:
                        if not isinstance(left_type, IntType) or not isinstance(right_type, IntType):
                            raise Exception(f"{loc}: {op} requires two integers, got {left_type} and {right_type}")
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
                if function == "print_int":
                    for arg in var_args:
                        if st.lookup(str(arg), Int) is None:
                            raise Exception(f"{loc}: {function} takes only int as argument")
                if function == "print_bool":
                    for arg in var_args:
                        if st.lookup(str(arg), Bool) is None:
                            raise Exception(f"{loc}: {function} takes only bool as argument")
                return var_result
            case ast.Block(statements=statements, result_expr=result_expr):
                block_sym_tab = SymTab({}, st)
                if result_expr is not None:
                    for i in range(len(statements) - 1):
                        visit(block_sym_tab, statements[i])
                    if final_expression:
                        return block_sym_tab
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
                if var_op is None:
                    raise Exception(f"{loc}: Unknown operator {neg}")
                var_operand = visit(st, expr)
                var_result, st = new_var(type, st)
                if str(var_op) == "unary_not":
                    if st.lookup(str(var_operand), Bool) is None:
                        raise Exception(f"{loc}: {var_operand} requires bool")
                elif str(var_op) == "unary_-":
                    if st.lookup(str(var_operand), Int) is None:
                        raise Exception(f"{loc}: {var_operand} requires int")
                ins.append(ir.Call(loc, var_op, [var_operand], var_result))
                return var_result
            case ast.VarDecl(name=name, initializer=initializer, type=type):
                t = Unit
                if isinstance(initializer, ast.Block):
                    if initializer.result_expr is not None:
                        if isinstance(initializer.result_expr.type, IntType):
                            t = Int
                        elif isinstance(initializer.result_expr.type, BoolType):
                            t = Bool
                        else:
                            raise Exception("ERROR HERE")
                    else:
                        raise Exception(f"{loc}: Block needs a result expression to be equal to variable")
                elif isinstance(initializer, ast.Call):
                    t = Int
                elif isinstance(type, IntType):
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
                    block_st = None
                    if isinstance(statements[-1], ast.Block):
                        block_st = visit(st, statements[-1], True)
                    if block_st is not None and result.function == "print_var":
                        if block_st.local_lookup(result.arguments[0].name, Int) is not None:
                            visit(block_st, ast.Call(location, "print_int", result.arguments), True)
                        elif block_st.local_lookup(result.arguments[0].name, Bool) is not None:
                            visit(block_st, ast.Call(location, "print_bool", result.arguments), True)
                    elif result.function == "print_var":
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

#string = """not (1 + 1)"""
#tokens = parser(string)
#ir_lines = generate_ir(GLOBAL_SYMTAB, tokens)
#for line in ir_lines:
#    print(line)
