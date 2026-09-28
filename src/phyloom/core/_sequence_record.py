from __future__ import annotations

from typing import TYPE_CHECKING

from phyloom.utils import MetadataMixin

if TYPE_CHECKING:
    from typing import Any


class SequenceRecord(MetadataMixin):
    """A sequence record in a multiple sequence alignment (MSA).

    Args:
        name: Sequence name.
        chars: Sequence characters. Must contain at least one character.
        **kwargs: Additional metadata associated with the sequence.
    """

    def __init__(self, name: str, chars: str, **kwargs: Any):
        if not chars:
            raise ValueError("Sequence must contain at least one character.")

        self._name = name
        self._chars = chars
        super().__init__(metadata=kwargs)

    @property
    def name(self) -> str:
        """Sequence name."""
        return self._name

    @property
    def chars(self) -> str:
        """Sequence characters."""
        return self._chars

    @property
    def n_chars(self) -> int:
        """Number of characters in the sequence."""
        return len(self.chars)

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(name={self.name!r}, n_chars={self.n_chars}, "
            f"metadata={dict(self.metadata)})"
        )
