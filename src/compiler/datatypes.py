from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class Type:
    """Basic type for types"""


@dataclass(frozen=True)
class IntType(Type):
    def __repr__(self):
        return "Int"


@dataclass(frozen=True)
class BoolType(Type):
    def __repr__(self):
        return "Bool"


@dataclass(frozen=True)
class UnitType(Type):
    def __repr__(self):
        return "Unit"


@dataclass(frozen=True)
class FunType(Type):
    param_types: List[Type]
    return_type: Type

    def __repr__(self):
        param_str = ", ".join(map(str, self.param_types))
        return f"({param_str}) -> {self.return_type}"

    def __eq__(self, other):
        return (isinstance(other, FunType) and self.param_types == other.param_types
                and self.return_type == other.return_type)


Int = IntType()
Bool = BoolType()
Unit = UnitType()
