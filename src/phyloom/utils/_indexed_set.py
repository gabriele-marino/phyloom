from __future__ import annotations

from collections.abc import Sequence
from collections.abc import Set as AbstractSet
from typing import TYPE_CHECKING, TypeVar, overload

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

T = TypeVar("T")


class IndexedSet(Sequence[T], AbstractSet[T]):
    """A set that supports integer indexing and sequence-style iteration.

    Membership checks, insertion, removal, and integer indexing take
    expected constant time.

    Args:
        items: Initial items to insert into the set.

    Examples:
        Maintain an indexed set of strings.

        >>> from phyloom.utils import IndexedSet
        >>> items = IndexedSet(["a", "b", "c"])
        >>> items[1], list(items)
        ('b', ['a', 'b', 'c'])
        >>> "b" in items, "d" in items
        (True, False)
        >>> len(items)
        3

        Adding an already-present item does not change the set.

        >>> items.add("a")
        >>> list(items)
        ['a', 'b', 'c']

        Removing an item may move the final item into its position,
        so the order of the remaining items is **not preserved**.

        >>> items.remove("a")
        >>> items[:]
        ['c', 'b']
    """

    def __init__(self, items: Iterable[T] = ()):
        self._items: list[T] = []
        self._index: dict[T, int] = {}
        for item in items:
            self.add(item)

    def add(self, item: T):
        """Add an item unless it is already present."""
        if item not in self._index:
            self._index[item] = len(self._items)
            self._items.append(item)

    def discard(self, item: T):
        """Remove an item if it is present."""
        if item in self._index:
            self.remove(item)

    def remove(self, item: T):
        """Remove an item."""
        i = self._index.pop(item)
        last = self._items.pop()
        if i != len(self._items):
            self._items[i] = last
            self._index[last] = i

    def __contains__(self, item: object) -> bool:
        """Return whether an item is present."""
        return item in self._index

    def __len__(self) -> int:
        """Return the number of items."""
        return len(self._items)

    def __iter__(self) -> Iterator[T]:
        """Iterate over items in their current indexed order."""
        return iter(self._items)

    @overload
    def __getitem__(self, index: int) -> T: ...
    @overload
    def __getitem__(self, index: slice) -> list[T]: ...
    def __getitem__(self, index: int | slice) -> T | list[T]:
        """Return an item by index or a list of items for a slice."""
        return self._items[index]
