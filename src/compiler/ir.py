from dataclasses import dataclass, fields
from tokenizer import Location
from typing import Any


@dataclass(frozen=True)
class IRVar:
    """Represents the name of a memory location or built-in"""
    name: str

    def __str__(self) -> str:
        return self.name


@dataclass(frozen=True)
class Instruction:
    """Base class for IR instructions"""
    location: Location

    def __str__(self) -> str:
        """Returns a string representation similar to IR code examples, e.g. 'LoadIntConst(3, x1)'"""
        def format_value(v: Any) -> str:
            if isinstance(v, list):
                return f'[{", ".join(format_value(e) for e in v)}]'
            else:
                return str(v)
        args = ', '.join(
            format_value(getattr(self, field.name)) for field in fields(self)
            if field.name != 'location'
        )
        return f'{type(self).__name__}({args})'


@dataclass(frozen=True)
class LoadBoolConst(Instruction):
    """Loads a boolean constant value to `dest`"""
    value: bool
    dest: IRVar


@dataclass(frozen=True)
class LoadIntConst(Instruction):
    """Loads constant value to `dest`"""
    value: int
    dest: IRVar


@dataclass(frozen=True)
class Copy(Instruction):
    """Copies a value from one variable to another"""
    source: IRVar
    dest: IRVar


@dataclass(frozen=True)
class Call(Instruction):
    """Calls a function or built-in"""
    fun: IRVar
    args: list[IRVar]
    dest: IRVar


@dataclass(frozen=True)
class Label(Instruction):
    """Marks the destination of a jump instruction"""
    name: str


@dataclass(frozen=True)
class Jump(Instruction):
    """Unconditionally continues execution from the given label"""
    label: Label


@dataclass(frozen=True)
class CondJump(Instruction):
    """Continues execution from the `then_label` if `cond` is true, otherwise from `else_label`"""
    cond: IRVar
    then_label: Label | None
    else_label: Label | None
    