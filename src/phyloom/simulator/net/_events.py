from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Generic

from phyloom.simulator.net._model import NetModelT_contra

if TYPE_CHECKING:
    from phyloom.types import NodeID


class LineageEventRule(Generic[NetModelT_contra]):
    """Base rule for single-lineage transition events in a network model.

    This class serves as an abstract base for stochastic events that target an
    individual active lineage—such as lineage termination, sampling, state
    transitions, or speciation. It handles candidate selection by counting eligible
    lineages and uniformly sampling one when the event executes, delegating the
    actual state modification to subclasses.

    Args:
        state: Optional state identifier used to restrict event eligibility to a
            matching subset of active lineages. Defaults to ``None`` (all active
            lineages eligible).
    """

    def __init__(self, state: str | None = None):
        self._state = state

    def opportunities(self, model: NetModelT_contra) -> int:
        """Count the number of currently eligible lineages."""
        return model.count_current_lineages(self._state)

    def apply(self, model: NetModelT_contra):
        """Uniformly sample an eligible lineage and delegate to :meth:`apply_to_lineage`."""
        (lineage,) = model.draw_current_lineages(self._state)
        self.apply_to_lineage(model, lineage)

    @abstractmethod
    def apply_to_lineage(self, model: NetModelT_contra, lineage: NodeID):
        """Apply the event transition to the selected lineage."""


class LineagePairEventRule(Generic[NetModelT_contra]):
    r"""Base rule for pairwise lineage interaction events in a network model.

    This class serves as an abstract base for stochastic events that operate on a
    pair of distinct active lineages—such as coalescence, reticulation, or gene
    flow. It provides automated candidate pair enumeration and uniform random
    sampling over eligible pairs, delegating the domain-specific transition logic
    to subclasses.

    Pair eligibility depends on the pair of state selectors provided during
    initialization:

    * **Unordered within-state pairs** (selectors are identical or no state restriction):
      Pair combinations are calculated without replacement
      (:math:`\binom{n}{2} = n(n - 1) / 2`), ensuring a lineage cannot interact
      with itself.
    * **Ordered cross-state pairs** (selectors are distinct values):
      Combinations are evaluated across the two candidate pools (:math:`n_1 \times n_2`).

    Args:
        states: Optional state identifiers for each participant in the interaction.
            Defaults to ``None`` (all active lineages eligible for unordered pairing).
    """

    def __init__(self, states: tuple[str, str] | None = None):
        self._state1, self._state2 = (None, None) if states is None else states

    def opportunities(self, model: NetModelT_contra) -> int:
        """Count the number of currently eligible lineage pairs."""
        n1 = model.count_current_lineages(self._state1)
        if self._state1 == self._state2:
            return n1 * (n1 - 1) // 2
        n2 = model.count_current_lineages(self._state2)
        return n1 * n2

    def apply(self, model: NetModelT_contra):
        """Uniformly sample an eligible lineage pair and apply the event transition.

        Draws a single pair of lineages from the candidate pool defined by the state
        selectors and delegates the transition to the subclass implementation of
        :meth:`apply_to_lineages`.
        """
        if self._state1 == self._state2:
            l1, l2 = model.draw_current_lineages(self._state1, 2)
            self.apply_to_lineages(model, (l1, l2))
        else:
            (l1,) = model.draw_current_lineages(self._state1)
            (l2,) = model.draw_current_lineages(self._state2)
            self.apply_to_lineages(model, (l1, l2))

    @abstractmethod
    def apply_to_lineages(
        self, model: NetModelT_contra, lineages: tuple[NodeID, NodeID]
    ):
        """Apply the event transition to the selected lineage pair."""
