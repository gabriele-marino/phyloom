"""Runtime age-dependent branching model."""

# This is the runtime Python model, on top of which the configuration layer
# builds.

from __future__ import annotations

from typing import TYPE_CHECKING

from phyloom.simulator.bdsh import BDSHModel

if TYPE_CHECKING:
    from collections.abc import Callable
    from typing import TypeAlias

    from typing_extensions import Self

    from phyloom.types import NodeID

StrOrNonePair: TypeAlias = tuple[str | None, str | None]


# BDSHModel already provides everything this process shares with a
# birth-death process: the root lineage, active lineages by state, lineage
# times, and the history as a tree. The subclass only decides *when* and *how*
# lineages end.
#
# Phyloom's stochastic events give every eligible lineage the same rate, as a
# function of the global clock, so they cannot express a rate that depends on
# a lineage's age. The model keeps the clock on the lineage instead: when a
# lineage is created, it draws the whole lifetime once and schedules an action,
# at the end of that lifetime, that resolves the lineage's fate.
class ADBModel(BDSHModel):
    """Binary age-dependent branching process with lineage states.

    Every lineage lives for a lifetime drawn from ``lifetime_func`` when it is
    created. At the end of its lifetime, it dies with probability
    ``death_prob``; otherwise, it is replaced by two child lineages, whose
    states are given by ``get_child_states``, and which start new lifetimes.

    Args:
        init_state: State of the initial lineage.
        lifetime_func: Callable returning the lifetime of a new lineage, given
            the model and the lineage's state.
        death_prob: Callable returning the probability that a lineage dies at
            the end of its lifetime, given the model and the lineage's state.
        get_child_states: Callable returning the states of the two children of
            a branching lineage, given the model and the parent's state. A
            ``None`` entry inherits the parent's state. If omitted, both
            children inherit the parent's state.

    Examples:
        Simulate a single-state process with Gamma lifetimes up to time 3.
        Every branch length is the lifetime drawn for that lineage, except for
        lineages still alive at ``max_time``, which are cut off there.

        >>> from phyloom_adb import ADBModel
        >>> model = ADBModel(
        ...     init_state="A",
        ...     lifetime_func=lambda m, state: m.rng.gammavariate(3.0, 0.5),
        ...     death_prob=lambda m, state: 0.3,
        ... )
        >>> model.rng.seed(1)
        >>> while model.step(max_time=3.0):
        ...     pass
        >>> model.history().pretty_print()
        1|A [0.6520373001841495]
        |-- 2|A [1.3699890442938663]
        `-- 3|A [0.928820891061326]
            |-- 4|A [1.359856854900276]
            |   |-- 6|A [0.05928495385424837]
            |   `-- 7|A [0.05928495385424837]
            `-- 5|A [1.4191418087545244]

        Deterministic callbacks make the process predictable, which is useful
        for testing. Here, ``A`` lineages live for one time unit and always
        split into an ``A`` and a ``B``, while ``B`` lineages live for half a
        unit and always die, so the tree grows as a caterpillar: every ``A``
        lineage lasts one unit, every ``B`` tip half a unit, and the last
        ``A`` lineage is cut off at ``max_time``.

        >>> model = ADBModel(
        ...     init_state="A",
        ...     lifetime_func=lambda m, state: {"A": 1.0, "B": 0.5}[state],
        ...     death_prob=lambda m, state: {"A": 0.0, "B": 1.0}[state],
        ...     get_child_states=lambda m, state: ("A", "B"),
        ... )
        >>> while model.step(max_time=2.5):
        ...     pass
        >>> model.history().pretty_print()
        1|A [1.0]
        |-- 2|B [0.5]
        `-- 3|A [1.0]
            |-- 4|B [0.5]
            `-- 5|A [0.5]
    """

    # The behavior comes in as callables, rather than, say, Gamma parameters,
    # so the model does not depend on any distribution: the configuration
    # decides what they compute.
    def __init__(
        self,
        init_state: str,
        lifetime_func: Callable[[Self, str], float],
        death_prob: Callable[[Self, str], float],
        get_child_states: Callable[[Self, str], StrOrNonePair] | None = None,
    ):
        super().__init__(init_state)
        self._lifetime_func = lifetime_func
        self._death_prob = death_prob
        if get_child_states is None:
            get_child_states = lambda _, state: (state, state)
        self._get_child_states = get_child_states
        # Start the root's clock at time zero, just as later clocks start when
        # their child lineages are created.
        self.add_action(0.0, lambda m: m._schedule_adb(m.get_root()))

    def _schedule_adb(self, lineage: NodeID):
        # A lineage's lifetime is drawn once, when it is created, and the action that
        # resolves it is scheduled at the end of that lifetime. Action times are
        # absolute, so the lifetime is added to the current time.
        self.add_action(
            self.current_time + self._lifetime_func(self, self.state_of(lineage)),
            lambda m: m.adb(lineage),
        )

    def adb(self, lineage: NodeID):
        """End a lineage's lifetime, with either a death or a branching."""
        # Both outcomes use BDSH primitives, which keep the state and history
        # bookkeeping: ``finalize`` records the end time without recording a
        # sample, and ``birth_from`` ends the lineage and creates two active
        # descendants. All randomness goes through the seeded ``self.rng``.
        if self.rng.random() < self._death_prob(self, self.state_of(lineage)):
            self.finalize(lineage)
            return
        child_states = self._get_child_states(self, self.state_of(lineage))
        first_child, second_child = self.birth_from(lineage, child_states)
        self._schedule_adb(first_child)
        self._schedule_adb(second_child)
