import ir
import dataclasses
from instrinsics import all_intrinsics, IntrinsicArgs


class Locals:
    """Knows the memory location of every local variable."""
    _var_to_location: dict[ir.IRVar, str]
    _stack_used: int

    def __init__(self, variables: list[ir.IRVar]) -> None:
        self._var_to_location = {}
        self._stack_used = 0
        for i, var in enumerate(variables, start=1):
            offset = -8 * i
            self._var_to_location[var] = f"{offset}(%rbp)"
        self._stack_used = len(variables) * 8

    def get_ref(self, v: ir.IRVar) -> str:
        """Returns an Assembly reference like `-24(%rbp)`
        for the memory location that stores the given variable"""
        #print(self._var_to_location)
        return self._var_to_location[v]

    def stack_used(self) -> int:
        """Returns the number of bytes of stack space needed for the local variables."""
        return self._stack_used

    def __len__(self):
        return len(self._var_to_location)


def get_all_ir_variables(instructions: list[ir.Instruction]) -> list[ir.IRVar]:
    result_list: list[ir.IRVar] = []
    result_set: set[ir.IRVar] = set()

    def add(v: ir.IRVar) -> None:
        if v not in result_set:
            result_list.append(v)
            result_set.add(v)

    for insn in instructions:
        match insn:
            case ir.LoadBoolConst(value=value, dest=dest):
                add(dest)
            case ir.LoadIntConst(value=value, dest=dest):
                add(dest)
            case ir.Copy(source=source, dest=dest):
                add(source)
                add(dest)
            case ir.Call(fun=fun, args=args, dest=dest):
                add(dest)
            case _:
                continue
    return result_list


def generate_assembly(instructions: list[ir.Instruction]) -> str:
    lines = []
    def emit(line: str) -> None: lines.append(line)
    locals = Locals(
        variables=get_all_ir_variables(instructions)
    )
    emit(".extern print_int")
    emit(".extern print_bool")
    emit(".extern read_int")
    emit(".section .text")
    emit(".global main")
    emit(".type main, @function")
    emit("main:")
    emit("pushq %rbp")
    emit("movq %rsp, %rbp")
    emit(f"subq ${8 * len(locals)}, %rsp")

    for insn in instructions:
        emit('# ' + str(insn))
        match insn:
            case ir.Label(name=name):
                emit("")
                emit(f'.{name}:')
            case ir.LoadIntConst(value=value, dest=dest):
                if -2**31 <= value < 2**31:
                    emit(f'movq ${value}, {locals.get_ref(dest)}')
                else:
                    emit(f'movabsq ${value}, %rax')
                    emit(f'movq %rax, {locals.get_ref(dest)}')
            case ir.Jump(label=label):
                emit(f'jmp .{label.name}')
            case ir.LoadBoolConst(value=value, dest=dest):
                bool_value = 1 if value else 0
                emit(f"movq ${bool_value}, {locals.get_ref(dest)}")
            case ir.Copy(source=source, dest=dest):
                emit(f"movq {locals.get_ref(source)}, %rax")
                emit(f"movq %rax, {locals.get_ref(dest)}")
            case ir.CondJump(cond=cond, then_label=then_label, else_label=else_label):
                emit(f"cmpq $0, {locals.get_ref(cond)}")
                if then_label:
                    emit(f"jne .{then_label.name}")
                if else_label:
                    emit(f"jmp .{else_label.name}")
            case ir.Call(fun=fun, args=args, dest=dest):
                arg_refs = [locals.get_ref(arg) for arg in args]
                if str(fun) in all_intrinsics:
                    all_intrinsics[str(fun)](IntrinsicArgs(
                        arg_refs=arg_refs,
                        result_register="%rax",
                        emit=emit
                    ))
                    emit(f"movq %rax, {locals.get_ref(dest)}")
                else:
                    for i, arg in enumerate(args[:6]):
                        emit(f"movq {arg_refs[i]}, %rdi")
                    emit(f"callq {fun}")
                    emit(f"movq %rax, {locals.get_ref(dest)}")
    emit("movq $0, %rax")
    emit("movq %rbp, %rsp")
    emit("popq %rbp")
    emit("ret")
    return "\n".join(lines)
