from __future__ import annotations

import heapq
from collections import defaultdict
from typing import TYPE_CHECKING, Generic, Protocol, TypeVar

if TYPE_CHECKING:
    from collections.abc import Iterable
    from typing import Any


class SupportsLT(Protocol):
    def __lt__(self, other: Any, /) -> bool: ...


KT = TypeVar("KT", bound=SupportsLT)
VT = TypeVar("VT")


class PriorityBuckets(Generic[KT, VT]):
    """A minimum-priority queue that groups values with equal keys.

    Each key identifies one bucket, and bucket values are kept in
    insertion order. Adding to an existing key and peeking at the
    smallest key takes constant time; adding a new key and removing
    the smallest key take logarithmic time in the number of keys.

    Args:
        items: Initial key-value pairs to insert.

    Examples:
        Maintain a priority queue of buckets with integer keys and string values.

        >>> from phyloom.utils import PriorityBuckets
        >>> buckets = PriorityBuckets([(2, "second"), (1, "first")])
        >>> buckets.push(1, "also first")
        >>> buckets.peek_key()
        1
        >>> len(buckets)
        2
        >>> buckets.pop()
        ['first', 'also first']
        >>> len(buckets), buckets.pop()
        (1, ['second'])
    """

    def __init__(self, items: Iterable[tuple[KT, VT]] = ()):
        self._buckets: defaultdict[KT, list[VT]] = defaultdict(list)
        for key, value in items:
            self._buckets[key].append(value)
        self._keys = list(self._buckets)
        heapq.heapify(self._keys)

    def push(self, key: KT, value: VT):
        """Add a value to the bucket for a key, creating the bucket if necessary."""
        if key not in self._buckets:
            heapq.heappush(self._keys, key)
        self._buckets[key].append(value)

    def peek_key(self) -> KT:
        """Return the smallest key without removing its bucket."""
        return self._keys[0]

    def pop(self) -> list[VT]:
        """Remove the smallest-key bucket and return its values."""
        return self._buckets.pop(heapq.heappop(self._keys))

    def copy(self) -> PriorityBuckets[KT, VT]:
        """Return a shallow copy of the queue."""
        return PriorityBuckets(
            (key, value) for key, values in self._buckets.items() for value in values
        )

    def __bool__(self) -> bool:
        """Return whether the queue contains at least one key."""
        return bool(self._keys)

    def __len__(self) -> int:
        """Return the number of keys in the queue."""
        return len(self._keys)
