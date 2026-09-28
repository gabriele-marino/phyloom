from __future__ import annotations

from collections import defaultdict
from types import MappingProxyType
from typing import TYPE_CHECKING, Generic

from phyloom.core._edge import LengthT_co

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

    from phyloom.core._edge import Edge
    from phyloom.core._node import Node
    from phyloom.types import NodeID, PathLike


class Net(Generic[LengthT_co]):
    """Phylogenetic network.

    A ``Net`` represents a rooted directed acyclic graph (DAG) in which every
    node is reachable from a distinguished root and edges are directed away
    from that root. Unlike a tree, a network may contain reticulation nodes
    with multiple parents while remaining acyclic. An optional stem edge can
    represent the branch leading into the network above the root.

    Args:
        nodes: Mapping from node ids to node records.
        edges: Mapping from directed ``(parent, child)`` node-id pairs to edge records.
        root: Root node id.
        stem: Optional stem edge attached above the root.

    Examples:
        Maintain a phylogenetic network with four nodes.

        >>> from phyloom.core import Net, Node, Edge
        >>> names = ["root", "left", "right", "reticulate"]
        >>> nodes = {i: Node(name) for i, name in enumerate(names)}
        >>> links = [(0, 1), (0, 2), (1, 3), (2, 3)]
        >>> edges = {link: Edge() for link in links}
        >>> net = Net(nodes, edges, root=0)
        >>> net.root, net.stem
        (0, None)
        >>> net.n_nodes, net.n_edges
        (4, 4)
        >>> [nodes[node].name for node in net]
        ['root', 'right', 'left', 'reticulate']
        >>> [nodes[parent].name for parent in net.parents_of(3)]
        ['left', 'right']
        >>> net.children_of(0)
        (1, 2)
        >>> net.is_leaf(0), net.is_leaf(3)
        (False, True)
        >>> net.get_leaves(), net.count_leaves()
        ((3,), 1)
        >>> net.is_internal(0), net.is_internal(3)
        (True, False)
        >>> net.get_internals(), net.count_internals()
        ((0, 2, 1), 3)
        >>> net.get_node_id("reticulate"), net.get_node("reticulate")
        (3, Node(name='reticulate', metadata={}))
        >>> net.pretty_print()
        root
        |-- left
        |   `-- reticulate
        `-- right
            `-- ref reticulate

        Cycles are rejected.

        >>> cyclic_edges = {**edges, (3, 1): Edge()}
        >>> Net(nodes, cyclic_edges, root=0)
        Traceback (most recent call last):
        ...
        ValueError: The network is not a DAG or is not fully connected from the root.

        Every node must be reachable from the root.

        >>> Net({**nodes, 4: Node("unreachable")}, edges, root=0)
        Traceback (most recent call last):
        ...
        ValueError: The network is not a DAG or is not fully connected from the root.
    """

    def __init__(
        self,
        nodes: Mapping[NodeID, Node],
        edges: Mapping[tuple[NodeID, NodeID], Edge[LengthT_co]],
        root: NodeID,
        stem: Edge[LengthT_co] | None = None,
    ):
        self._nodes = dict(nodes)

        self._edges_from: dict[NodeID, list[NodeID]] = defaultdict(list)
        self._edges_to: dict[NodeID, list[NodeID]] = defaultdict(list)
        for from_node, to_node in edges:
            self._check_node(from_node)
            self._check_node(to_node)
            self._edges_from[from_node].append(to_node)
            self._edges_to[to_node].append(from_node)
        self._edges = dict(edges)

        if self.parents_of(root):
            raise ValueError("The root node has parents.")
        self._root = root
        self._stem = stem

        if len(nodes) != sum(1 for _ in self):
            raise ValueError(
                "The network is not a DAG or is not fully connected from the root."
            )

    @property
    def nodes(self) -> Mapping[NodeID, Node]:
        """Read-only mapping from node ids to node records."""
        return MappingProxyType(self._nodes)

    @property
    def n_nodes(self) -> int:
        """Number of nodes in the network."""
        return len(self._nodes)

    @property
    def edges(self) -> Mapping[tuple[NodeID, NodeID], Edge[LengthT_co]]:
        """Read-only mapping from directed (parent, child) node-id pairs to edge records."""
        return MappingProxyType(self._edges)

    @property
    def n_edges(self) -> int:
        """Number of edges in the network."""
        return len(self._edges)

    @property
    def root(self) -> NodeID:
        """Root node id."""
        return self._root

    @property
    def stem(self) -> Edge[LengthT_co] | None:
        """Stem edge attached above the root."""
        return self._stem

    def _check_node(self, id_: NodeID):
        if id_ not in self._nodes:
            raise ValueError(f"Node {id_} not found.")

    def children_of(self, node: NodeID) -> tuple[NodeID, ...]:
        """Get the children of a node."""
        self._check_node(node)
        return tuple(self._edges_from[node])

    def parents_of(self, node: NodeID) -> tuple[NodeID, ...]:
        """Get the parents of a node."""
        self._check_node(node)
        return tuple(self._edges_to[node])

    def is_leaf(self, node: NodeID) -> bool:
        """Check if a node is a leaf (has no children)."""
        return not self.children_of(node)

    def get_leaves(self) -> tuple[NodeID, ...]:
        """Get all leaf nodes."""
        return tuple(filter(self.is_leaf, self))

    def count_leaves(self) -> int:
        """Count the number of leaf nodes."""
        return len(self.get_leaves())

    def is_internal(self, node: NodeID) -> bool:
        """Check if a node is internal (has at least one child)."""
        return bool(self.children_of(node))

    def get_internals(self) -> tuple[NodeID, ...]:
        """Get all internal nodes."""
        return tuple(filter(self.is_internal, self))

    def count_internals(self) -> int:
        """Count the number of internal nodes."""
        return len(self.get_internals())

    def get_node_id(self, name: str) -> NodeID:
        """Get a node id by its name."""
        for node_id, node in self.nodes.items():
            if node.name == name:
                return node_id
        raise ValueError(f"No node with name {name} found.")

    def get_node(self, name: str) -> Node:
        """Get a node record by its name."""
        node_id = self.get_node_id(name)
        return self.nodes[node_id]

    def to_newick(self) -> str:
        """Serialize the network into a Newick string."""
        from phyloom.io import to_newick

        return to_newick(self)

    def dump(self, filepath: PathLike):
        """Write the network to a Newick file."""
        from phyloom.io import dump_newick

        dump_newick([self], filepath)

    def pretty_print(self):
        """Print a human-readable representation of the network."""
        from phyloom.core._algo import pprint_net

        pprint_net(self)

    def __iter__(self) -> Iterator[NodeID]:
        """Iterate over the nodes in the network in a topological order (parents before children)."""
        from phyloom.core._algo import iter_net

        yield from iter_net(self)

    def __repr__(self) -> str:
        return f"{type(self).__name__}(n_nodes={self.n_nodes}, n_edges={self.n_edges})"
