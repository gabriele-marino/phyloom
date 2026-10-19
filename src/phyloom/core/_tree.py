from __future__ import annotations

from typing import TYPE_CHECKING

from phyloom.core._edge import LengthT_co
from phyloom.core._net import Net

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from phyloom.core._edge import Edge
    from phyloom.core._node import Node
    from phyloom.types import NodeID


class Tree(Net[LengthT_co]):
    """Phylogenetic tree.

    A ``Tree`` represents a rooted directed tree in which every node is reachable
    from a distinguished root, and edges are directed away from that root. Unlike
    a network, a tree contains no reticulation nodes with multiple parents:
    every node except the root has exactly one parent. An optional stem edge can
    represent the branch leading into the tree above the root.

    Args:
        nodes: Mapping from node ids to node records.
        edges: Mapping from directed ``(parent, child)`` node-id pairs to edge records.
        root: Root node id.
        stem: Optional stem edge attached above the root.

    Examples:
        Maintain a phylogenetic tree with five nodes.

        >>> from phyloom.core import Edge, Node, Tree
        >>> names = ["root", "left", "right", "left-left", "left-right"]
        >>> nodes = {i: Node(name) for i, name in enumerate(names)}
        >>> links = [(0, 1), (0, 2), (1, 3), (1, 4)]
        >>> lengths = [0.2, 0.3, 0.4, 0.5]
        >>> edges = {link: Edge(length) for link, length in zip(links, lengths)}
        >>> tree = Tree(nodes, edges, root=0, stem=Edge(length=0.1))
        >>> tree.root
        0
        >>> tree.nodes[tree.parent_of(4)].name
        'left'
        >>> tree.children_of(1)
        (3, 4)
        >>> tree.get_leaves(), tree.count_leaves()
        ((2, 4, 3), 3)
        >>> tree.get_internals(), tree.count_internals()
        ((0, 1), 2)
        >>> tree.edge_of(0).length, tree.edge_of(4).length
        (0.1, 0.5)
        >>> tree.is_binary()
        True
        >>> tree.get_mrca([3, 4])
        1
        >>> tree.get_path(3, 2)
        [3, 1, 0, 2]

        Reticulation nodes are rejected.

        >>> nodes = {i: Node(str(i)) for i in range(4)}
        >>> links = [(0, 1), (0, 2), (1, 3), (2, 3)]
        >>> edges = {link: Edge() for link in links}
        >>> Tree(nodes, edges, root=0)
        Traceback (most recent call last):
        ...
        ValueError: The network is not a tree: some nodes have more than one parent.

    """

    def __init__(
        self,
        nodes: Mapping[NodeID, Node],
        edges: Mapping[tuple[NodeID, NodeID], Edge[LengthT_co]],
        root: NodeID,
        stem: Edge[LengthT_co] | None = None,
    ):
        super().__init__(nodes, edges, root, stem)

        if any(len(self.parents_of(node)) > 1 for node in self):
            raise ValueError(
                "The network is not a tree: some nodes have more than one parent."
            )

    def parent_of(self, node: NodeID) -> NodeID:
        """Get the unique parent of a node."""
        if node == self.root:
            raise ValueError("The root node has no parent.")
        (parent,) = self.parents_of(node)
        return parent

    def edge_of(self, node: NodeID) -> Edge[LengthT_co]:
        """Get the edge leading into a node."""
        if node == self.root:
            if self.stem is None:
                raise ValueError("The root node has no stem edge.")
            return self.stem
        return self.edges[(self.parent_of(node), node)]

    def is_binary(self) -> bool:
        """Check whether every internal node has exactly two children."""
        return all(len(self.children_of(node)) == 2 for node in self.get_internals())

    def get_mrca(self, nodes: Iterable[NodeID]) -> NodeID:
        """Get the most recent common ancestor of two nodes."""
        from phyloom.core._algo import iter_tree_upward

        nodes = set(nodes)
        if len(nodes) < 2:
            raise ValueError(
                f"At least two differentnodes are required to find a most recent common ancestor (got {len(nodes)})."
            )
        for node in nodes:
            self._check_node(node)

        first, *rest = nodes
        other_ancestors = [set(iter_tree_upward(self, node)) for node in rest]
        for ancestor in iter_tree_upward(self, first):
            if all(ancestor in other for other in other_ancestors):
                return ancestor
        raise AssertionError("All nodes in a valid tree must share an ancestor.")

    def get_path(self, from_node: NodeID, to_node: NodeID) -> list[NodeID]:
        """Get the path between two nodes, including both endpoints."""
        from phyloom.core._algo import iter_tree_upward

        mrca = self.get_mrca([from_node, to_node])
        return [
            *iter_tree_upward(self, from_node, stop=mrca),
            mrca,
            *reversed(list(iter_tree_upward(self, to_node, stop=mrca))),
        ]

    def ladderize(self):
        """Sort each node's children by the number of descendant leaves.

        The tree is modified in place. Children with fewer descendant leaves
        are placed first.

        Examples:
            >>> from phyloom.core import Edge, Node, Tree
            >>> nodes = {i: Node(str(i)) for i in range(5)}
            >>> links = [(0, 2), (0, 1), (2, 3), (2, 4)]
            >>> edges = {link: Edge() for link in links}
            >>> tree = Tree(nodes, edges, root=0)
            >>> tree.pretty_print()
            0
            |-- 2
            |   |-- 3
            |   `-- 4
            `-- 1
            >>> tree.ladderize()
            >>> tree.pretty_print()
            0
            |-- 1
            `-- 2
                |-- 3
                `-- 4
        """
        from phyloom.core._algo import count_descendant_leaves

        key = count_descendant_leaves(self)
        for node in self.get_internals():
            self._edges_from[node].sort(key=key.__getitem__)
        self._edges = {
            (node, child): self._edges[(node, child)]
            for node in self
            for child in self.children_of(node)
        }
