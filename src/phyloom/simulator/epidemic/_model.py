from __future__ import annotations

from collections import defaultdict
from types import MappingProxyType
from typing import TYPE_CHECKING

from phyloom.core import Edge
from phyloom.simulator.net import NetModel
from phyloom.utils import SetView

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Mapping

    from typing_extensions import Self

    from phyloom.simulator.core import Event
    from phyloom.types import NodeID


class EpidemicModel(NetModel):
    """Compartmental epidemic model.

    The model evolves a rooted network forward in time from one initial infectious
    lineage. Epidemic dynamics are represented by two complementary components:
    :attr:`pools`, which stores counts of individuals in named compartments
    such as ``S``, ``I``, and ``R``, and the transmission network, which stores
    active lineages and their discrete ``state`` labels. The model also records
    sampled lineages: finalized lineages designated as observations that can be
    used to extract the portion of the history ancestral to the observed data.
    Although the pool and network states are maintained independently, events
    may update both. For example, an infection removes an individual from a
    recipient pool and replaces one active source lineage with two descendants,
    whereas a recovery terminates a lineage and returns an individual to a
    destination pool.

    Its lineage and population primitives are:

    * :meth:`infection` consumes one individual from a recipient pool and
      replaces an active source lineage with two descendants;
    * :meth:`recovery` ends a lineage, returns one individual to a destination
      pool, and optionally records that lineage as sampled;
    * :meth:`migration` replaces a lineage with one child in the same or a
      new state (migration or another state change); and
    * :meth:`flow` moves one individual between pools without changing the
      lineage network.

    Args:
        init_state: State of the initial infectious lineage.
        init_pools: Initial non-negative counts for each population pool.
        events: Stochastic events governing continuous-time state transitions.
        schedule: Iterable of ``(time, action)`` pairs. An action receives and
            mutates the model when its time is reached. Actions scheduled for
            the same time are shuffled before execution.

    Examples:
        This deterministic SIR-like history exposes infection, recovery with
        and without sampling, migration, and pool flow. Lineage ids are
        allocated in creation order, which makes the network changes easy
        to follow. It starts with one infectious lineage and three susceptible
        individuals, and ends with four recovered individuals, two of which are
        sampled.

        >>> from phyloom.simulator.epidemic import EpidemicModel
        >>> schedule = [
        ...     (1, lambda m: m.infection(1, "S")),
        ...     (2, lambda m: m.infection(3, "S")),
        ...     (3, lambda m: m.recovery(2, "R", sample=True)),
        ...     (4, lambda m: m.migration(4, "I")),
        ...     (5, lambda m: m.flow("S", "R")),
        ...     (6, lambda m: m.recovery(5, "R")),
        ...     (7, lambda m: m.recovery(6, "R", sample=True)),
        ... ]
        >>> model = EpidemicModel(init_state="I", init_pools={"S": 3}, schedule=schedule)
        >>> while model.step():
        ...     pass
        >>> dict(model.pools), list(model.get_current_lineages())
        ({'S': 0, 'R': 4}, [])
        >>> sorted(model.get_sampled_lineages())
        [2, 6]

        The full history contains every transmission lineage, including the
        unsampled lineages and the unobserved path between the two sampled leaves:

        >>> model.history().pretty_print()
        1|I [1.0]
        |-- 2|I [2]
        `-- 3|I [1]
            |-- 4|I [2]
            |   `-- 6|I [3]
            `-- 5|I [4]

        Passing the sampled lineages as a skeleton compresses away unobserved
        paths and returns the sampled network:

        >>> sampled = model.history(model.get_sampled_lineages())
        >>> sampled.pretty_print()
        1|I [1.0]
        |-- 2|I [2]
        `-- 6|I [6]
    """

    def __init__(
        self,
        init_state: str,
        init_pools: Mapping[str, int],
        events: Iterable[Event[Self]] = (),
        schedule: Iterable[tuple[float, Callable[[Self], None]]] = (),
    ):
        super().__init__(events, schedule)
        for compartment, count in init_pools.items():
            if count < 0:
                raise ValueError(
                    f"Initial count for compartment '{compartment}' must "
                    f"be non-negative (got {count})."
                )
        self._pools = defaultdict(int, init_pools)
        self._root = self._get_new_lineage(init_state)
        self._sampled_lineages: dict[str, set[NodeID]] = defaultdict(set)
        self._all_sampled_lineages: set[NodeID] = set()
        self._times: dict[NodeID, float] = {}

    def get_root(self) -> NodeID:
        """Return the initial lineage as the root of the history."""
        return self._root

    def time_of(self, lineage: NodeID) -> float:
        """Return the time at which ``lineage`` was finalized.

        An active lineage is treated as ending at
        :attr:`~phyloom.simulator.core.Model.current_time`, which
        allows a history to be materialized before all lineages
        recover.
        """
        return self._times.get(lineage, self.current_time)

    @property
    def origin(self) -> float:
        """Return ``0.0``, the start of forward simulation time."""
        return 0.0

    @property
    def pools(self) -> Mapping[str, int]:
        """Read-only mapping of compartment names to current counts."""
        return MappingProxyType(self._pools)

    def _decrement(self, compartment: str):
        if not self._pools[compartment]:
            raise ValueError(
                f"Cannot decrement compartment '{compartment}': it is already empty."
            )
        self._pools[compartment] -= 1

    def _increment(self, compartment: str):
        self._pools[compartment] += 1

    def flow(self, source: str, destination: str):
        """Move one individual from ``source`` to ``destination``.

        Pool flow changes compartment counts only; it does not create,
        finalize, or sample a lineage.

        Args:
            source: Pool to decrement.
            destination: Pool to increment.
        """
        self._decrement(source)
        self._increment(destination)

    def _finalize(self, lineage: NodeID):
        if lineage in self._times:
            raise RuntimeError(f"Lineage {lineage} has already been finalized.")
        self._times[lineage] = self.current_time
        self._finalize_lineage(lineage)

    def recovery(self, lineage: NodeID, destination_pool: str, *, sample: bool = False):
        """End an active lineage, return one individual to a destination pool, and optionally record that lineage as sampled.

        Args:
            lineage: Active lineage that recovers.
            destination_pool: Pool receiving the recovered individual.
            sample: Whether to record the finalized lineage as a sample.
        """
        self._finalize(lineage)
        self._increment(destination_pool)
        if sample:
            self._sampled_lineages[self.state_of(lineage)].add(lineage)
            self._all_sampled_lineages.add(lineage)

    def migration(self, lineage: NodeID, new_state: str | None = None) -> NodeID:
        """Replace an active lineage with one continuing child.

        Args:
            lineage: Active lineage to continue.
            new_state: Optional state assigned to the child. If omitted, the
                child inherits its parent's state.

        Returns:
            The new active child lineage id.
        """
        self._finalize(lineage)
        child = self._get_new_lineage(
            new_state if new_state is not None else self.state_of(lineage)
        )
        self._edges[(lineage, child)] = Edge()
        return child

    def infection(
        self,
        parent: NodeID,
        recipient_pool: str,
        child_states: tuple[str | None, str | None] = (None, None),
    ) -> tuple[NodeID, NodeID]:
        """Replace one active lineage with two descendants and decrement a recipient pool.

        Args:
            parent: Active lineage on which the infection occurs.
            recipient_pool: Pool from which the infected individual is removed.
            child_states: Optional pair of states assigned to the descendant
                lineages. A ``None`` entry inherits the parent's state.

        Returns:
            The pair of new active child lineage ids, in the same order as ``child_states``.
        """
        self._decrement(recipient_pool)
        continuing_state, child_state = child_states
        child = self._get_new_lineage(
            child_state if child_state is not None else self.state_of(parent)
        )
        self._edges[(parent, child)] = Edge()
        continuing = self.migration(parent, continuing_state)
        return continuing, child

    def _get_sampled_lineages(self, state: str | None = None) -> set[NodeID]:
        if state is None:
            return self._all_sampled_lineages
        return self._sampled_lineages[state]

    def get_sampled_lineages(self, state: str | None = None) -> SetView[NodeID]:
        """Read-only view of sampled lineage ids, optionally restricted to one state."""
        return SetView(self._get_sampled_lineages(state))

    def count_sampled_lineages(self, state: str | None = None) -> int:
        """Count sampled lineages, optionally restricted to one state."""
        return len(self._get_sampled_lineages(state))
