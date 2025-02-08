import ir
import astree as ast
from datatypes import Bool, Int, Type, Unit
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
    var_types: dict[ir.IRVar, Type] = root_types.locals.copy()
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
                    if not isinstance(left, ast.Identifier):
                        raise Exception(f"{loc}: Left side of assignment must be a variable")
                    var_left = st.lookup(left.name)
                    var_right = visit(st, right)
                    ins.append(ir.Copy(loc, var_right, var_left))
                    return var_left
                elif op in {"and", "or"}:
                    l_end = new_label(loc)
                    var_left = visit(st, left)
                    var_result = new_var(Bool)
                    if op == "and":
                        ins.append(ir.CondJump(loc, var_left, None, l_end))
                    else:
                        ins.append(ir.CondJump(loc, var_left, l_end, None))
                    var_right = visit(st, right)
                    ins.append(ir.Copy(loc, var_right, var_result))
                    ins.append(l_end)
                    return var_result
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
                var_func = visit(st, function)
                var_args = [visit(st, arg) for arg in arguments]
                var_result = new_var(expr.type)
                ins.append(ir.Call(loc, var_func, var_args, var_result))
                return var_result
            case ast.Block(statements=statements, result_expr=result_expr):
                for stmt in statements:
                    visit(st, stmt)
                return var_unit
            case ast.UnaryOp(op=op, expr=expr):
                var_op = st.lookup(op)
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
            case ast.Program(statements=statements):
                for stmt in statements:
                    visit(st, stmt)
                return var_unit
            case _:
                raise Exception(f"{loc}: Unknown AST node type: {type(ast)}")

    root_sym_tab = SymTab(locals={})
    for v in root_types.locals.keys():
        root_sym_tab.locals[v.name] = v
    var_final_result = visit(root_sym_tab, root_expr)
    if var_types[var_final_result] == Int:
        ins.append(ir.Call(root_expr.location, ir.IRVar("print_int"), [var_final_result], var_unit))
    elif var_types[var_final_result] == Bool:
        ins.append(ir.Call(root_expr.location, ir.IRVar("print_bool"), [var_final_result], var_unit))
    return ins


parsed = parser("""
while x > 0 do {
x = x - 1
}
""")
root_types = SymTab({ir.IRVar("x"): Int, ir.IRVar(">"): Int, ir.IRVar("-"): Int})
instructions = generate_ir(root_types, parsed)
for inst in instructions:
    print(inst)
