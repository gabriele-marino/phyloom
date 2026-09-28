from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

    from phyloom.core._net import Net
    from phyloom.core._tree import Tree
    from phyloom.types import NodeID


def iter_net(net: Net[float | None]) -> Iterator[NodeID]:
    queue = [net.root]
    visited: set[NodeID] = set()
    while queue:
        node = queue.pop()
        yield node
        visited.add(node)

        for child in net.children_of(node):
            if all(parent in visited for parent in net.parents_of(child)):
                queue.append(child)


def iter_tree_upward(
    tree: Tree[float | None], start: NodeID, stop: NodeID | None = None
) -> Iterator[NodeID]:
    node = start
    while True:
        if node == stop:
            return
        yield node
        if node == tree.root:
            if stop is None:
                return
            raise ValueError("Reached root without encountering stop node.")
        node = tree.parent_of(node)
