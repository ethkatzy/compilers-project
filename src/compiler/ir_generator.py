import ir
import astree as ast
from datatypes import Bool, Int, Type, Unit, IntType, BoolType
from tokenizer import Location
from parser import parser
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class SymTab:
    locals: dict[ir.IRVar, Type]
    parent: Optional["SymTab"] = None

    def lookup(self, name) -> Any:
        if name in self.locals:
            return self.locals[name]
        else:
            raise NameError(f"Undefined symbol: {name}")


def generate_ir(root_types: dict[ir.IRVar, Type], root_expr: ast.Expression) -> list[ir.Instruction]:
    var_types: dict[ir.IRVar, Type] = root_types.copy()
    var_unit = ir.IRVar('unit')
    var_types[var_unit] = Unit

    counter = 1
    ins: list[ir.Instruction] = []
    label_counter = 1

    def new_var(t: Type) -> ir.IRVar:
        nonlocal counter
        var = ir.IRVar(f"x{counter}")
        var_types[var] = t
        counter += 1
        return var

    def new_label(loc: Location) -> ir.Label:
        nonlocal label_counter
        label_name = ir.Label(loc, f"L{label_counter}")
        label_counter += 1
        return label_name

    def visit(st: SymTab, expr: ast.Expression) -> ir.IRVar:
        loc = expr.location
        match expr:
            case ast.Literal(value=value):
                match value:
                    case bool():
                        var = new_var(Bool)
                        ins.append(ir.LoadBoolConst(loc, value, var))
                    case int():
                        var = new_var(Int)
                        ins.append(ir.LoadIntConst(loc, value, var))
                    case None:
                        var = var_unit
                    case _:
                        raise Exception(f"{loc}: unsupported literal: {type(value)}")
                return var
            case ast.Identifier(name=name):
                return st.lookup(name)
            case ast.BinaryOp(left=left, op=op, right=right):
                if op == "=":
                    if not (isinstance(left, ast.BinaryOp) and left.op == "="):
                        if not isinstance(left, ast.Identifier):
                            raise Exception(f"{loc}: Left side of assignment must be a variable")
                        var_left = st.lookup(left.name)
                        var_right = visit(st, right)
                        ins.append(ir.Copy(loc, var_right, var_left))
                        return var_left
                    else:
                        var_right = visit(st, right)
                        ins.append(ir.Copy(loc, var_right, st.lookup(left.right.name)))
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
                    extra_var = new_var(Bool)
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
                    var_op = st.lookup(op)
                    var_left = visit(st, left)
                    var_right = visit(st, right)
                    var_result = new_var(expr.type)
                    ins.append(ir.Call(loc, var_op, [var_left, var_right], var_result))
                    return var_result
            case ast.IfExpr(condition=condition, then_expr=then_expr, else_expr=else_expr):
                l_then = new_label(loc)
                l_else = new_label(loc) if else_expr else None
                l_end = new_label(loc)
                var_cond = visit(st, condition)
                ins.append(ir.CondJump(loc, var_cond, l_then, l_else or l_end))
                ins.append(l_then)
                var_then = visit(st, then_expr)
                ins.append(ir.Jump(loc, l_end))
                if else_expr:
                    ins.append(l_else)
                    var_else = visit(st, else_expr)
                ins.append(l_end)
                return var_then if not else_expr else new_var(expr.type)
            case ast.Call(function=function, arguments=arguments):
                var_func = ir.IRVar(function)
                var_args = [visit(st, arg) for arg in arguments]
                var_result = new_var(expr.type)
                ins.append(ir.Call(loc, var_func, var_args, var_result))
                return var_result
            case ast.Block(statements=statements, result_expr=result_expr):
                for stmt in statements:
                    visit(st, stmt)
                return var_unit
            case ast.UnaryOp(op=op, expr=expr):
                if op == "-":
                    neg = "unary_-"
                    var_op = st.lookup(neg)
                else:
                    neg = "unary_not"
                    var_op = st.lookup(neg)
                var_operand = visit(st, expr)
                var_result = new_var(expr.type)
                ins.append(ir.Call(loc, var_op, [var_operand], var_result))
                return var_result
            case ast.VarDecl(name=name, initializer=initializer):
                var_value = visit(st, initializer)
                var_decl = new_var(expr.type)
                st.locals[name] = var_decl
                ins.append(ir.Copy(loc, var_value, var_decl))
                return var_unit
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
                    if result.function == "print_var":
                        if isinstance(root_types[ir.IRVar(result.arguments[0].name)], IntType):
                            visit(st, ast.Call(location, "print_int", result.arguments))
                        elif isinstance(root_types[ir.IRVar(result.arguments[0].name)], BoolType):
                            visit(st, ast.Call(location, "print_bool", result.arguments))
                    else:
                        visit(st, result)
                else:
                    for stmt in statements:
                        visit(st, stmt)
                return var_unit
            case _:
                raise Exception(f"{loc}: Unknown AST node type: {type(ast)}")

    root_sym_tab = SymTab(locals={})
    for v in root_types.keys():
        root_sym_tab.locals[v.name] = v
    var_final_result = visit(root_sym_tab, root_expr)
    return ins


def extract_identifiers(node: ast.Expression, symTab: SymTab) -> SymTab:
    """ Recursively extracts all identifier names from the AST and adds them to symTab with type Int. """
    match node:
        case ast.VarDecl(name=name, initializer=initializer):
            if name not in symTab.locals:
                if isinstance(node.type, IntType):
                    symTab.locals[ir.IRVar(name)] = Int
                    return symTab
                elif isinstance(node.type, BoolType):
                    symTab.locals[ir.IRVar(name)] = Bool
                    return symTab
                else:
                    symTab.locals[ir.IRVar(name)] = symTab.locals[ir.IRVar(initializer.name)]
                    return symTab
        case ast.IfExpr(condition=condition, then_expr=then_expr, else_expr=else_expr):
            symTab = extract_identifiers(then_expr, symTab)
            if else_expr is not None:
                symTab = extract_identifiers(else_expr, symTab)
            return symTab
        case ast.Call(function=function, arguments=arguments):
            for stmt in arguments:
                symTab = extract_identifiers(stmt, symTab)
            return symTab
        case ast.Block(statements=statements, result_expr=result_expr):
            for stmt in statements:
                symTab = extract_identifiers(stmt, symTab)
            return symTab
        case ast.Program(statements=statements):
            for stmt in statements:
                symTab = extract_identifiers(stmt, symTab)
            return symTab
        case ast.While(condition=condition, statements=statements):
            for stmt in statements:
                symTab = extract_identifiers(stmt, symTab)
            return symTab
        case _:
            return symTab


GLOBAL_SYMTAB = SymTab({ir.IRVar("+"): Int,
                        ir.IRVar("-"): Int,
                        ir.IRVar("*"): Int,
                        ir.IRVar("/"): Int,
                        ir.IRVar("%"): Int,
                        ir.IRVar("<"): Bool,
                        ir.IRVar("<="): Bool,
                        ir.IRVar("=="): Bool,
                        ir.IRVar(">="): Bool,
                        ir.IRVar(">"): Bool,
                        ir.IRVar("!="): Bool,
                        ir.IRVar("unary_-"): Int,
                        ir.IRVar("unary_not"): Bool,
                        ir.IRVar("print_int"): Int,
                        ir.IRVar("print_bool"): Bool,
                        ir.IRVar("read_int"): Unit,
                        })

root_types = SymTab({}, GLOBAL_SYMTAB)

string = """var a = 3;
var b = 4;
var c = 5;
a = b = c;
print_int(a);
print_int(b);
print_int(c);"""
tokens = parser(string)
sym_tab = extract_identifiers(tokens, GLOBAL_SYMTAB)
ir_lines = generate_ir(sym_tab.locals, tokens)
for line in ir_lines:
    print(line)