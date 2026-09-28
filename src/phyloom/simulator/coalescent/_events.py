from __future__ import annotations

from typing import TYPE_CHECKING

from phyloom.simulator.coalescent._model import CoalescentModel
from phyloom.simulator.net import LineageEventRule, LineagePairEventRule

if TYPE_CHECKING:
    from phyloom.types import NodeID


class Retrace(LineageEventRule[CoalescentModel]):
    """Retrace event that replaces one active lineage with an ancestral parent.

    Args:
        ancestral_state: State assigned to the new parent.
        current_state: Optional state restricting eligible lineages.
    """

    def __init__(self, ancestral_state: str, current_state: str | None = None):
        super().__init__(current_state)
        self._ancestral_state = ancestral_state

    def apply_to_lineage(self, model: CoalescentModel, lineage: NodeID):
        """Replace the selected lineage with an ancestral parent."""
        model.retrace(lineage, self._ancestral_state)


class Coalesce(LineagePairEventRule[CoalescentModel]):
    """Coalescence event that replaces two active lineages with one ancestral parent.

    Args:
        current_states: Optional pair of states restricting the child pair.
        ancestral_state: Optional state assigned to the ancestral parent. If
            omitted, the child lineages must share the same state, which the
            parent inherits.
    """

    def __init__(
        self,
        current_states: tuple[str, str] | None = None,
        ancestral_state: str | None = None,
    ):
        super().__init__(current_states)
        self._ancestral_state = ancestral_state

    def apply_to_lineages(
        self, model: CoalescentModel, lineages: tuple[NodeID, NodeID]
    ):
        """Replace the selected lineage pair with one ancestral parent."""
        model.coalesce(lineages, state=self._ancestral_state)
