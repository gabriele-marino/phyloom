from __future__ import annotations

from typing import TYPE_CHECKING, Generic, TypeVar

from phyloom.utils import MetadataMixin

if TYPE_CHECKING:
    from typing import Any


LengthT_co = TypeVar("LengthT_co", bound=float | None, covariant=True)


class Edge(MetadataMixin, Generic[LengthT_co]):
    """A directed edge in a phylogenetic tree or network.

    Args:
        length: Optional edge length.
        kwargs: Additional metadata associated with the edge.
    """

    def __init__(self, length: LengthT_co = None, **kwargs: Any):
        if length is not None and length < 0:
            raise ValueError(f"Edge length must be non-negative (got {length}).")

        self._length = length
        super().__init__(metadata=kwargs)

    @property
    def length(self) -> LengthT_co:
        """Edge length."""
        return self._length

    def __repr__(self) -> str:
        return f"{type(self).__name__}(length={self.length}, metadata={dict(self.metadata)})"
