from __future__ import annotations

from typing import TYPE_CHECKING

from phyloom.core import Edge
from phyloom.simulator.net import NetModel

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Mapping

    from typing_extensions import Self

    from phyloom.simulator.core import Event
    from phyloom.types import NodeID


class CoalescentModel(NetModel):
    """Backwards-time genealogy model.

    This model evolves a rooted network backwards in time from an initial
    population of lineages. Simulation advances backwards from the observed
    lineages toward their ancestors.
    :attr:`~phyloom.simulator.core.Model.current_time` therefore increases
    into the past, while lineage times are stored as its negative so that
    older ancestors have smaller coordinates. The active set represents
    lineages still being traced backwards.

    The model's primitives are:

    * :meth:`spawn`, which creates a new active lineage at the current time;
    * :meth:`retrace`, which replaces one active lineage by an ancestral
      parent in another state; and
    * :meth:`coalesce`, which replaces two active lineages by one parent and
      connects both children to it.

    Coalescent histories do not maintain a sampled-lineage set. A complete
    history can be materialized only after the active lineages have been
    reduced to one root.

    Args:
        init_population: Positive number of initial active lineages for each
            state.
        events: Stochastic events governing continuous-time state transitions.
        schedule: Iterable of ``(time, action)`` pairs. An action receives and
            mutates the model when its time is reached. Actions scheduled for
            the same time are shuffled before execution.

    Examples:
        This deterministic schedule starts with two ``A`` lineages, spawns a
        third, retraces one through a ``B`` ancestor, then coalesces the
        lineages into an ``A/B`` ancestor.

        >>> from phyloom.simulator.coalescent import CoalescentModel
        >>> schedule = [
        ...     (1, lambda m: m.spawn("A")),
        ...     (2, lambda m: m.retrace(1, "B")),
        ...     (3, lambda m: m.coalesce((2, 3), state="A")),
        ...     (4, lambda m: m.coalesce((4, 5), state="A/B")),
        ... ]
        >>> model = CoalescentModel(init_population={"A": 2}, schedule=schedule)
        >>> while model.step(max_time=5):
        ...     pass
        >>> model.history().pretty_print()
        6|A/B [1]
        |-- 4|B [2]
        |   `-- 1|A [2.0]
        `-- 5|A [1]
            |-- 2|A [3.0]
            `-- 3|A [2]
    """

    def __init__(
        self,
        init_population: Mapping[str, int],
        events: Iterable[Event[Self]] = (),
        schedule: Iterable[tuple[float, Callable[[Self], None]]] = (),
    ):
        super().__init__(events, schedule)
        if not init_population:
            raise ValueError("Initial population cannot be empty.")
        for state, size in init_population.items():
            if not size > 0:
                raise ValueError(
                    f"Initial population size for state '{state}' must be positive (got {size})."
                )
        self._init_population = init_population
        self._times: dict[NodeID, float] = {}
        for state, size in self._init_population.items():
            for _ in range(size):
                self.spawn(state)

    def get_root(self) -> NodeID:
        """Return the sole remaining active lineage as the root.

        The genealogy must have fully coalesced before this method is called.
        """
        if len(self._all_current_lineages) > 1:
            raise RuntimeError(
                f"Cannot construct the net: the genealogy has not fully coalesced yet "
                f"({len(self._all_current_lineages)} current lineages remain)."
            )
        (root,) = self._all_current_lineages
        return root

    def time_of(self, lineage: NodeID) -> float:
        """Return the backwards-time coordinate assigned to a lineage."""
        return self._times[lineage]

    @property
    def origin(self) -> float:
        """Return the current simulation origin in backwards-time coordinates."""
        return -self.current_time

    def spawn(self, state: str) -> NodeID:
        """Create a new active lineage in the given state at the current time.

        Args:
            state: State of the new lineage.

        Returns:
            The new active lineage id.
        """
        new = self._get_new_lineage(state)
        self._times[new] = -self.current_time
        return new

    def coalesce(
        self, lineages: tuple[NodeID, NodeID], state: str | None = None
    ) -> NodeID:
        """Replace two active lineages with one ancestral parent.

        Args:
            lineages: Pair of active child lineage ids.
            state: Optional state assigned to the new parent. If omitted, both
                children must share a state, which the parent inherits.

        Returns:
            The new active parent lineage id.
        """
        if state is None:
            states = {self.state_of(l) for l in lineages}
            if len(states) > 1:
                raise ValueError(
                    f"Cannot coalesce lineages with different states: {states}"
                )
            (state,) = states
        parent = self.spawn(state)
        for l in lineages:
            self._finalize_lineage(l)
            self._edges[(parent, l)] = Edge()
        return parent

    def retrace(self, lineage: NodeID, state: str) -> NodeID:
        """Replace one active lineage with an ancestral parent in ``state``.

        Args:
            lineage: Active lineage to retrace.
            state: State assigned to the new ancestral parent.

        Returns:
            The new active parent lineage id.
        """
        parent = self.spawn(state)
        self._edges[(parent, lineage)] = Edge()
        self._finalize_lineage(lineage)
        return parent
