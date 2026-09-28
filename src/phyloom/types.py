"""Common type aliases used throughout the package."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from typing import TypeAlias


#: Materialized sample-specific context for a simulation run.
#: Alias of :class:`dict`\[:class:`str`, :class:`object`].
Context: TypeAlias = dict[str, object]

#: Arbitrary string-keyed metadata attached to phylogenetic objects.
#: Alias of :class:`~collections.abc.Mapping`\[:class:`str`, :obj:`~typing.Any`].
Metadata: TypeAlias = Mapping[str, Any]

#: Identifier assigned to a node in a tree or network.
#: Alias of :class:`int`.
NodeID: TypeAlias = int

#: A file-system path or string representation of a path.
#: Alias of :class:`str` | :class:`~pathlib.Path`.
PathLike: TypeAlias = str | Path

#: Identifier assigned to a sample in a simulation run.
#: Alias of :class:`int`.
SampleID: TypeAlias = int

#: Initial state for a pseudo-random number generator.
#: Alias of :class:`int`.
Seed: TypeAlias = int

__all__ = ["Context", "Metadata", "NodeID", "PathLike", "SampleID", "Seed"]
