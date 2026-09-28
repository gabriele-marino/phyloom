from __future__ import annotations

from typing import TYPE_CHECKING

from phyloom.simulator.bdsh._model import BDSHModel
from phyloom.simulator.net import LineageEventRule, LineagePairEventRule

if TYPE_CHECKING:
    from phyloom.types import NodeID


class Birth(LineageEventRule[BDSHModel]):
    """Birth event that replaces one active lineage with two descendants.

    Args:
        parent_state: Optional state restricting eligible parent lineages.
        child_states: Optional pair of states assigned to the descendant lineages.
            A ``None`` entry inherits the parent's state.
    """

    def __init__(
        self,
        parent_state: str | None = None,
        child_states: tuple[str | None, str | None] = (None, None),
    ):
        super().__init__(parent_state)
        self._child_states = child_states

    def apply_to_lineage(self, model: BDSHModel, lineage: NodeID):
        """Replace the selected lineage with two descendants."""
        model.birth_from(lineage, child_states=self._child_states)


class Death(LineageEventRule[BDSHModel]):
    """Death event that finalizes one active lineage without sampling it.

    Args:
        state: Optional state restricting eligible lineages.
    """

    def apply_to_lineage(self, model: BDSHModel, lineage: NodeID):
        """Finalize the selected lineage without sampling it."""
        return model.finalize(lineage)


class Migration(LineageEventRule[BDSHModel]):
    """State-change event that replaces one active lineage with a continuing child.

    Args:
        source_state: State restricting eligible parent lineages.
        target_state: State assigned to the child lineage.
    """

    def __init__(self, source_state: str, target_state: str):
        super().__init__(source_state)
        self.target_state = target_state

    def apply_to_lineage(self, model: BDSHModel, lineage: NodeID):
        """Replace the selected lineage with a continuing child in the target state."""
        model.continue_as(lineage, self.target_state)


class Sampling(LineageEventRule[BDSHModel]):
    """Sampling event that records one eligible active lineage.

    Args:
        state: Optional state restricting eligible lineages.
        removal: Whether to end the sampled lineage. If ``False``, the lineage
            first branches; one descendant is recorded as the
            sample at the current time, and the other remains active.
    """

    def __init__(
        self,
        state: str | None = None,
        *,
        removal: bool,
    ):
        super().__init__(state)
        self.removal = removal

    def apply_to_lineage(self, model: BDSHModel, lineage: NodeID):
        """Record the selected lineage as a sample."""
        model.sample(lineage, removal=self.removal)


class LDH(LineagePairEventRule[BDSHModel]):
    """Lineage-degenerative hybridization (LDH) event that replaces two active lineages with one hybrid child.

    Args:
        parent_states: Optional pair of states restricting the two parent lineages.
        hybrid_state: Optional state assigned to the hybrid child. If omitted,
            the parents must share the same state, which the child inherits.
    """

    def __init__(
        self,
        parent_states: tuple[str, str] | None = None,
        hybrid_state: str | None = None,
    ):
        super().__init__(parent_states)
        self._hybrid_state = hybrid_state

    def apply_to_lineages(self, model: BDSHModel, lineages: tuple[NodeID, NodeID]):
        """Replace the selected lineage pair with one hybrid child."""
        model.hybridize(lineages, hybrid_state=self._hybrid_state)


class LNH(LineagePairEventRule[BDSHModel]):
    """Lineage-neutral hybridization (LNH) event.

    Models a combined speciation-hybridization event where an active lineage
    gives birth to an intermediate offspring that immediately hybridizes with
    a second active lineage. The primary parent lineage continues (with an
    optional state transition), while its new offspring merges with the secondary
    parent to form a hybrid lineage.

    Args:
        continuing_parent_state: Optional state restricting the primary
            (birth-giving) parent lineage.
        terminating_parent_state: Optional state restricting the secondary
            (hybridizing) parent lineage.
        new_parent_state: Optional state assigned to the continuing primary
            (birth-giving) parent lineage. If omitted, the continuing lineage
            inherits the parent's state.
        hybrid_state: Optional state assigned to the resulting hybrid lineage.
            If omitted, the parents must share the same state, which the
            child inherits.
    """

    def __init__(
        self,
        continuing_parent_state: str | None = None,
        terminating_parent_state: str | None = None,
        new_parent_state: str | None = None,
        hybrid_state: str | None = None,
    ):
        if (continuing_parent_state is None) != (terminating_parent_state is None):
            raise ValueError(
                "Both continuing and terminating parent states must be specified, "
                f"or neither (got continuing_parent_state={continuing_parent_state}, "
                f"terminating_parent_state={terminating_parent_state})"
            )

        if continuing_parent_state is None or terminating_parent_state is None:
            super().__init__(None)
        else:
            super().__init__((continuing_parent_state, terminating_parent_state))

        self._new_parent_state = new_parent_state
        self._hybrid_state = hybrid_state

    def apply_to_lineages(self, model: BDSHModel, lineages: tuple[NodeID, NodeID]):
        """Hybridize an offspring of the first selected lineage with the second selected lineage."""
        parent1, parent2 = lineages
        _, child = model.birth_from(
            parent1, child_states=(self._new_parent_state, None)
        )
        model.hybridize((parent2, child), hybrid_state=self._hybrid_state)


class LGH(LineagePairEventRule[BDSHModel]):
    """Lineage-generative hybridization (LGH) event.

    Models a dual-speciation hybridization event where two active parent
    lineages each give birth to a child lineage, and those two child lineages
    then hybridize. Both original parent lineages continue as active branches,
    while their offspring combine into a single hybrid lineage.

    Args:
        parent_states: Optional pair of states restricting the two parent lineages.
        hybrid_state: Optional state assigned to the resulting hybrid lineage.
            If omitted, the parents must share the same state, which the
            child inherits.
        new_parent_states: Optional pair of states assigned to the continuing
            parent lineages, in the same order as ``parent_states``. A ``None``
            entry inherits the parent's state.
    """

    def __init__(
        self,
        parent_states: tuple[str, str] | None = None,
        hybrid_state: str | None = None,
        new_parent_states: tuple[str | None, str | None] = (None, None),
    ):
        super().__init__(parent_states)
        self._hybrid_state = hybrid_state
        self._continuing_state1, self._continuing_state2 = new_parent_states

    def apply_to_lineages(self, model: BDSHModel, lineages: tuple[NodeID, NodeID]):
        """Hybridize one offspring of each selected lineage, keeping both lineages active."""
        parent1, parent2 = lineages
        _, child1 = model.birth_from(
            parent1, child_states=(self._continuing_state1, None)
        )
        _, child2 = model.birth_from(
            parent2, child_states=(self._continuing_state2, None)
        )
        model.hybridize((child1, child2), hybrid_state=self._hybrid_state)
