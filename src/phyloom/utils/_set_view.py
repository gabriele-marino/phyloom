from __future__ import annotations

from collections.abc import Set as AbstractSet
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from collections.abc import Iterator

T = TypeVar("T")


class SetView(AbstractSet[T]):
    """A read-only, live view of an abstract set.

    Args:
        s: Set to wrap.
    """

    def __init__(self, s: AbstractSet[T]):
        self._set = s

    def __contains__(self, x: object) -> bool:
        """Return whether an item is present in the wrapped set."""
        return x in self._set

    def __iter__(self) -> Iterator[T]:
        """Iterate over the wrapped set."""
        return iter(self._set)

    def __len__(self) -> int:
        """Return the number of items in the wrapped set."""
        return len(self._set)
