from __future__ import annotations

from typing import TYPE_CHECKING

from phyloom.utils import MetadataMixin

if TYPE_CHECKING:
    from typing import Any


class Node(MetadataMixin):
    """A node in a phylogenetic tree or network.

    Args:
        name: Node name.
        kwargs: Additional metadata associated with the node.
    """

    def __init__(self, name: str = "", **kwargs: Any):
        self._name = name
        super().__init__(metadata=kwargs)

    @property
    def name(self) -> str:
        """Node name."""
        return self._name

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(name={self.name!r}, metadata={dict(self.metadata)})"
        )
