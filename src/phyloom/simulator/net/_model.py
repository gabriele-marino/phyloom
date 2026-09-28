from __future__ import annotations

from abc import ABC, abstractmethod
from collections import defaultdict
from types import MappingProxyType
from typing import TYPE_CHECKING, TypeVar, overload

from phyloom.core import Edge, Net, Node, Tree
from phyloom.simulator.core import Model
from phyloom.utils import IndexedSet, SetView

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Mapping
    from typing import Literal

    from typing_extensions import Self

    from phyloom.simulator.core import Event
    from phyloom.types import NodeID

NetModelT_contra = TypeVar("NetModelT_contra", bound="NetModel", contravariant=True)


class NetModel(ABC, Model):
    """Base abstraction for simulations that build phylogenetic networks.

    A ``NetModel`` maintains the network constructed during a run as
    collections of ``nodes`` and directed ``edges``. Nodes are lineage records,
    and an edge relates a parent lineage to a descendant lineage created from
    it.

    Lineages are organized into states, which can be used to select lineages
    for events. States are represented by strings, and their biological
    interpretation is model-defined. A lineage is active while it exists at
    the current simulation time and can be changed by a subsequent event.
    :meth:`get_current_lineages`, :meth:`count_current_lineages`, and
    :meth:`draw_current_lineages` respectively provide access to, count, and
    draw active lineages.

    Subclasses must supply model-specific primitives to evolve active lineages
    through time, for example by replacing one or more lineages with their
    descendants and define :meth:`time_of`, :meth:`get_root`, and :attr:`origin`
    to describe the network's timing and extent. This supports both forward-time
    models and backward-time models, such as coalescents.

    The full history is exposed through :meth:`history`. A skeleton can be
    supplied when only the ancestry of selected leaf lineages is needed, for
    example to obtain the history relevant to observed or sampled data while
    omitting unobserved parts of the simulation.

    Args:
        events: Stochastic events governing continuous-time state transitions.
        schedule: Iterable of ``(time, action)`` pairs. An action receives and
            mutates the model when its time is reached. Actions scheduled for
            the same time are shuffled before execution.
    """

    def __init__(
        self,
        events: Iterable[Event[Self]] = (),
        schedule: Iterable[tuple[float, Callable[[Self], None]]] = (),
    ):
        super().__init__(events, schedule)
        self._nodes: dict[NodeID, Node] = {}
        self._edges: dict[tuple[NodeID, NodeID], Edge[None]] = {}
        self._stem = Edge()
        self._states: dict[NodeID, str] = {}
        self._next_lineage_id = 0
        self._all_current_lineages: IndexedSet[NodeID] = IndexedSet()
        self._current_lineages: defaultdict[str, IndexedSet[NodeID]] = defaultdict(
            IndexedSet[int]
        )

    @property
    def nodes(self) -> Mapping[NodeID, Node]:
        """Read-only mapping of lineage node ids to node records."""
        return MappingProxyType(self._nodes)

    @property
    def edges(self) -> Mapping[tuple[NodeID, NodeID], Edge[None]]:
        """Read-only mapping from directed ``(parent, child)`` node-id pairs to edge records."""
        return MappingProxyType(self._edges)

    @abstractmethod
    def get_root(self) -> NodeID:
        """Root node id of the history built by the run."""

    @property
    def stem(self) -> Edge[None]:
        """Stem edge connecting the history root to the origin time above it."""
        return self._stem

    @property
    @abstractmethod
    def origin(self) -> float:
        """Simulation origin time, preceding the history root."""

    @abstractmethod
    def time_of(self, lineage: NodeID) -> float:
        """Return the model time associated with a lineage node.

        :meth:`history` uses lineage times to set the length of an edge from
        ``parent`` to ``child`` to ``time_of(child) - time_of(parent)``. The
        stem length is ``time_of(get_root()) - origin``.
        """

    def state_of(self, lineage: NodeID) -> str:
        """Return the state assigned to a lineage node."""
        return self._states[lineage]

    def _get_new_lineage(self, state: str) -> NodeID:
        self._next_lineage_id += 1
        lineage = self._next_lineage_id
        self._nodes[lineage] = Node(f"{lineage}|{state}")
        self._states[lineage] = state
        self._all_current_lineages.add(lineage)
        self._current_lineages[state].add(lineage)
        return lineage

    def _finalize_lineage(self, lineage: NodeID):
        self._all_current_lineages.remove(lineage)
        self._current_lineages[self.state_of(lineage)].remove(lineage)

    def _get_current_lineages(self, state: str | None = None) -> IndexedSet[NodeID]:
        return (
            self._all_current_lineages
            if state is None
            else self._current_lineages[state]
        )

    def get_current_lineages(self, state: str | None = None) -> SetView[NodeID]:
        """Return active lineages, optionally restricted to a state."""
        return SetView(self._get_current_lineages(state))

    def count_current_lineages(self, state: str | None = None) -> int:
        """Return the number of active lineages, optionally restricted to a state."""
        return len(self._get_current_lineages(state))

    def draw_current_lineages(
        self, state: str | None = None, k: int = 1
    ) -> list[NodeID]:
        """Uniformly draw ``k`` active lineage ids without replacement, optionally restricted to a state."""
        pool = self._get_current_lineages(state)
        n = len(pool)
        if k > n:
            raise ValueError(f"Cannot draw {k} lineages from a total of {n} lineages.")
        if k == 1:
            return [pool[self.rng.randrange(n)]]
        return self.rng.sample(pool, k)

    @overload
    def history(
        self, skeleton: Iterable[NodeID] | None = None, *, return_as: Literal["tree"]
    ) -> Tree[float]: ...
    @overload
    def history(
        self,
        skeleton: Iterable[NodeID] | None = None,
        *,
        return_as: Literal["net"] = "net",
    ) -> Net[float]: ...
    def history(
        self,
        skeleton: Iterable[NodeID] | None = None,
        *,
        return_as: Literal["net", "tree"] = "net",
    ) -> Net[float]:
        """Return the simulated history as a network or tree.

        Without a ``skeleton``, the result is the full history of the run:
        every lineage and relationship produced by the simulation. With a
        skeleton, the result is the ancestry of the selected leaf lineages,
        including their shared ancestry but excluding unrelated lineages.

        Args:
            skeleton: Leaf lineage ids that define the history to return. The
                result contains their shared ancestry, rather than lineages
                unrelated to them. This is useful when the full simulation
                includes lineages outside the observed or sampled history. If
                omitted, return the full simulated history.
            return_as: Whether to return the history as a tree or a network.

        Returns:
            The full simulated history or the ancestry of the selected leaf
            lineages.
        """
        constructor = Tree[float] if return_as == "tree" else Net[float]
        if skeleton is None:
            root = self.get_root()
            edges = {
                (parent, child): Edge(
                    self.time_of(child) - self.time_of(parent), **edge.metadata
                )
                for (parent, child), edge in self._edges.items()
            }
            stem = Edge(self.time_of(root) - self.origin, **self.stem.metadata)
            return constructor(self._nodes, edges, root, stem)

        net = Net(self._nodes, self._edges, self.get_root(), self.stem)
        skeleton = set(skeleton)
        if not skeleton:
            raise ValueError("Skeleton cannot be empty.")
        if not all(net.is_leaf(node) for node in skeleton):
            raise ValueError(
                "All nodes in the skeleton must be leaf nodes of the network."
            )

        nodes: dict[NodeID, Node] = {}
        edges: dict[tuple[NodeID, NodeID], Edge[float]] = {}
        first_included_reachable: dict[NodeID, NodeID] = {}

        for node in reversed(list(net)):
            persisting_children = {
                first_included_reachable[child]
                for child in net.children_of(node)
                if child in first_included_reachable
            }
            if len(persisting_children) > 1 or node in skeleton:
                nodes[node] = net.nodes[node]
                first_included_reachable[node] = node
                for child in persisting_children:
                    edges[(node, child)] = Edge(
                        self.time_of(child) - self.time_of(node)
                    )
            elif len(persisting_children) == 1:
                (persisting_child,) = persisting_children
                first_included_reachable[node] = persisting_child

        new_root = first_included_reachable[net.root]
        stem = Edge(self.time_of(new_root) - self.origin)
        return constructor(nodes, edges, new_root, stem)
