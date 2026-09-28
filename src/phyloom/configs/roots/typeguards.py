"""Typeguards for type-safe evaluation of Python source code in configuration."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Generic, TypeVar

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import TypeGuard


T = TypeVar("T")


def is_bool(value: object) -> TypeGuard[bool]:
    """Check if a value is a bool."""
    return isinstance(value, bool)


def is_int(value: object) -> TypeGuard[int]:
    """Check if a value is an int (but not a bool)."""
    return isinstance(value, int) and not isinstance(value, bool)


def is_float(value: object) -> TypeGuard[float]:
    """Check if a value is a float (or an int, but not a bool)."""
    return isinstance(value, int | float) and not isinstance(value, bool)


def is_sequence(value: object) -> TypeGuard[Sequence[object]]:
    """Check if a value is a sequence (but not a string)."""
    return isinstance(value, Sequence) and not isinstance(value, str)


def is_float_sequence(value: object) -> TypeGuard[Sequence[float]]:
    """Check if a value is a sequence of floats."""
    return is_sequence(value) and all(map(is_float, value))


@dataclass
class NamedTypeguard(Generic[T]):
    """A typeguard paired with a human-readable name used in error messages.

    Args:
        name: Description of the expected type.
        fn: Function that checks whether a value has the expected type.
    """

    name: str
    fn: Callable[[object], TypeGuard[T]]


#: Typeguard accepting a bool.
BOOL_TG = NamedTypeguard("bool", is_bool)
#: Typeguard accepting an int, but not a bool.
INT_TG = NamedTypeguard("int", is_int)
#: Typeguard accepting a float or an int, but not a bool.
FLOAT_TG = NamedTypeguard("float", is_float)
#: Typeguard accepting a sequence of floats.
FLOAT_SEQUENCE_TG = NamedTypeguard("sequence of floats", is_float_sequence)
