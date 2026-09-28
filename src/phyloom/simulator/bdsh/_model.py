from __future__ import annotations

from collections import defaultdict
from typing import TYPE_CHECKING

from phyloom.core import Edge
from phyloom.simulator.net import NetModel
from phyloom.utils import SetView

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from typing_extensions import Self

    from phyloom.simulator.core import Event
    from phyloom.types import NodeID


class BDSHModel(NetModel):
    """Birth-death-sampling-hybridization model.

    The model evolves a rooted network forward in time from one initial
    lineage. Alongside the active lineages inherited from
    :class:`~phyloom.simulator.net.NetModel`, it records sampled lineages:
    finalized lineages designated as observations. The sampled set can be
    used to extract the part of the history ancestral to the observed data.

    The model exposes a small set of lineage primitives:

    * :meth:`birth_from` replaces one active lineage with a continuing
      lineage and a new child lineage;
    * :meth:`continue_as` replaces a lineage with one child, optionally in a
      new state (migration or state change);
    * :meth:`finalize` ends an active lineage without sampling it (death);
    * :meth:`sample` ends and records a lineage, or, with ``removal=False``,
      records a sample while leaving a new active descendant; and
    * :meth:`hybridize` replaces two active parents with one hybrid child that
      has two incoming edges.

    Args:
        init_state: State of the initial active lineage.
        events: Stochastic events governing continuous-time state transitions.
        schedule: Iterable of ``(time, action)`` pairs. An action receives and
            mutates the model when its time is reached. Actions scheduled for
            the same time are shuffled before execution.

    Examples:
        The following deterministic schedule calls every kind of lineage
        primitive. Lineage ids are allocated in creation order, which makes the
        network changes easy to follow. The hybridization creates a reticulation
        in the full history; only ids 6 and 9 are sampled.

        >>> from phyloom.simulator.bdsh import BDSHModel
        >>> schedule = [
        ...     (1, lambda m: m.birth_from(1)),
        ...     (2, lambda m: m.birth_from(2)),
        ...     (3, lambda m: m.continue_as(3, "B")),
        ...     (4, lambda m: m.hybridize((4, 5), hybrid_state="H")),
        ...     (5, lambda m: m.rho_sample(1.0, "B", removal=True)),
        ...     (6, lambda m: m.sample(7, removal=False)),
        ...     (7, lambda m: m.finalize(8)),
        ... ]
        >>> model = BDSHModel(init_state="A", schedule=schedule)
        >>> while model.step():
        ...     pass
        >>> list(model.get_current_lineages()), sorted(model.get_sampled_lineages())
        ([], [6, 9])

        The full history contains every lineage, including the unsampled
        lineages and the unobserved paths between the two sampled leaves:

        >>> model.history().pretty_print()
        1|A [1.0]
        |-- 2|A [1]
        |   |-- 4|A [2]
        |   |   `-- 7|H [2]
        |   |       |-- 8|H [1]
        |   |       `-- 9|H [0]
        |   `-- 5|A [2]
        |       `-- ref 7|H [2]
        `-- 3|A [2]
            `-- 6|B [2]

        Passing the sampled lineages as a skeleton compresses away unobserved
        paths and returns the sampled network:

        >>> sampled = model.history(model.get_sampled_lineages())
        >>> sampled.pretty_print()
        1|A [1.0]
        |-- 9|H [5]
        `-- 6|B [4]
    """

    def __init__(
        self,
        init_state: str,
        events: Iterable[Event[Self]] = (),
        schedule: Iterable[tuple[float, Callable[[Self], None]]] = (),
    ):
        super().__init__(events, schedule)
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
        have been finalized.
        """
        return self._times.get(lineage, self.current_time)

    @property
    def origin(self) -> float:
        """Return ``0.0``, the start of forward simulation time."""
        return 0.0

    def finalize(self, lineage: NodeID):
        """End an active lineage without sampling it.

        This is the primitive used for death or any other unobserved terminal
        outcome. The lineage remains in the model history but is removed from
        the active lineage sets.

        Args:
            lineage: Active lineage to end.
        """
        if lineage in self._times:
            raise RuntimeError(f"Lineage {lineage} has already been finalized.")
        self._times[lineage] = self.current_time
        self._finalize_lineage(lineage)

    def sample(self, lineage: NodeID, *, removal: bool):
        """Record an active lineage as a sample.

        Args:
            lineage: Active lineage to record.
            removal: Whether to end the sampled lineage. If ``False``, the
                lineage first branches; one descendant is recorded as the
                sample at the current time, and the other remains active.
        """
        if not removal:
            lineage, _ = self.birth_from(lineage)
        self.finalize(lineage)
        self._sampled_lineages[self.state_of(lineage)].add(lineage)
        self._all_sampled_lineages.add(lineage)

    def rho_sample(self, p: float, state: str | None = None, *, removal: bool):
        """Independently sample eligible active lineages.

        Args:
            p: Sampling probability for each eligible lineage.
            state: Optional state restricting eligible lineages.
            removal: Whether to end sampled lineages. If ``False``, each
                sampled lineage first branches; one descendant is recorded
                as the sample at the current time, and the other remains active.
        """
        for lineage in list(self._get_current_lineages(state)):
            if self.rng.random() < p:
                self.sample(lineage, removal=removal)

    def continue_as(self, lineage: NodeID, new_state: str | None = None) -> NodeID:
        """Replace an active lineage with one continuing child.

        Args:
            lineage: Active lineage to continue.
            new_state: Optional state of the child lineage. If omitted,
                the child inherits the parent's state.

        Returns:
            The new active child lineage id.
        """
        self.finalize(lineage)
        child = self._get_new_lineage(
            new_state if new_state is not None else self.state_of(lineage)
        )
        self._edges[(lineage, child)] = Edge()
        return child

    def birth_from(
        self,
        parent: NodeID,
        child_states: tuple[str | None, str | None] = (None, None),
    ) -> tuple[NodeID, NodeID]:
        """Replace one active parent lineage with two active descendant lineages.

        Args:
            parent: Active lineage on which the birth occurs.
            child_states: Optional pair of states assigned to the descendant
                lineages. A ``None`` entry inherits the parent's state.

        Returns:
            The pair of new active child lineage ids, in the same order as ``child_states``.
        """
        continuing_state, child_state = child_states
        child = self._get_new_lineage(
            child_state if child_state is not None else self.state_of(parent)
        )
        self._edges[(parent, child)] = Edge()
        continuing = self.continue_as(parent, continuing_state)
        return continuing, child

    def hybridize(
        self, parents: tuple[NodeID, NodeID], hybrid_state: str | None = None
    ) -> NodeID:
        """Replace two active parent lineages with one hybrid child.

        Args:
            parents: Pair of active parent lineage ids.
            hybrid_state: Optional state of the hybrid child. If omitted, the
                parents must share the same state, which the child inherits.

        Returns:
            The new active hybrid lineage id.
        """
        if hybrid_state is None:
            states = {self.state_of(parent) for parent in parents}
            if len(states) > 1:
                raise ValueError(
                    "Cannot infer hybrid state from parents with different states."
                )
            (hybrid_state,) = states
        hybrid = self._get_new_lineage(hybrid_state)
        for parent in parents:
            self.finalize(parent)
            self._edges[(parent, hybrid)] = Edge()
        return hybrid

    def get_sampled_lineages(self, state: str | None = None) -> SetView[NodeID]:
        """Read-only view of sampled lineage ids, optionally restricted to one state."""
        if state is None:
            return SetView(self._all_sampled_lineages)
        return SetView(self._sampled_lineages[state])

    def count_sampled_lineages(self, state: str | None = None) -> int:
        """Count sampled lineages, optionally restricted to one state."""
        return len(self.get_sampled_lineages(state))
