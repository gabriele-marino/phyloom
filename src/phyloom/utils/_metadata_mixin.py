from __future__ import annotations

from types import MappingProxyType
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing import Any

    from phyloom.types import Metadata


class MetadataMixin:
    """Mixin for objects that carry arbitrary metadata.

    Metadata is stored as key-value pairs and can be accessed through explicit
    methods such as :meth:`set`, :meth:`get`, and :meth:`update`, or with item
    syntax.

    Args:
        metadata: Initial metadata to store.

    Examples:
        Maintain arbitrary metadata for an object using the mixin.

        >>> from typing import Any
        >>> from phyloom.utils import MetadataMixin
        >>> class Store(MetadataMixin):
        ...     def __init__(self, **kwargs: Any):
        ...         super().__init__(metadata=kwargs)
        >>> store = Store(state="S", time=0.0)
        >>> dict(store.metadata)
        {'state': 'S', 'time': 0.0}
        >>> store.set("state", "I")
        >>> store["state"]
        'I'
        >>> store["time"] = 1.5
        >>> store.get("time")
        1.5
        >>> store.update({"host": "human", "state": "R"})
        >>> store.get("state")
        'R'
        >>> store.get("missing", "fallback")
        'fallback'
        >>> "state" in store
        True
        >>> dict(store.metadata)
        {'state': 'R', 'time': 1.5, 'host': 'human'}
        >>> store.delete("host")
        >>> "host" in store
        False
        >>> store.clear()
        >>> dict(store.metadata)
        {}
    """

    def __init__(
        self,
        *args: Any,
        metadata: Metadata | None = None,
        **kwargs: Any,
    ):
        super().__init__(*args, **kwargs)
        self._metadata: dict[str, Any] = {} if metadata is None else dict(metadata)

    @property
    def metadata(self) -> Metadata:
        """Read-only view of the stored metadata."""
        return MappingProxyType(self._metadata)

    def set(self, key: str, value: Any):
        """Set one metadata value by key."""
        self._metadata[key] = value

    def update(self, metadata: Metadata):
        """Update multiple metadata values from a mapping of key-value pairs."""
        self._metadata.update(metadata)

    def get(self, key: str, default: Any = None) -> Any:
        """Return one metadata value by key, or a default if the key is not present."""
        return self._metadata.get(key, default)

    def delete(self, key: str):
        """Delete one metadata value by key."""
        del self._metadata[key]

    def clear(self):
        """Remove all metadata."""
        self._metadata.clear()

    def __getitem__(self, key: str) -> Any:
        """Return one metadata value with item syntax."""
        return self._metadata[key]

    def __setitem__(self, key: str, value: Any):
        """Set one metadata value with item syntax."""
        self._metadata[key] = value

    def __delitem__(self, key: str):
        """Delete one metadata value with item syntax."""
        del self._metadata[key]

    def __contains__(self, key: str) -> bool:
        """Return whether a metadata key is present."""
        return key in self._metadata
