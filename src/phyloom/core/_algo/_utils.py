from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from phyloom.core._net import Net
    from phyloom.types import NodeID


def count_descendant_leaves(net: Net[float | None]) -> dict[NodeID, int]:
    counts: dict[NodeID, int] = {}
    for node in reversed(list(net)):
        children = net.children_of(node)
        counts[node] = sum(counts[child] for child in children) if children else 1
    return counts
