"""Stochastic event rules of the contact-tracing model."""

# An event rule counts the eligible transitions (``opportunities``) and applies
# one of them (``apply``). All three rules act on a single lineage, so they
# inherit both methods from LineageEventRule: the opportunities are the active
# lineages in the rule's state (all active lineages if the state is ``None``),
# and ``apply`` draws one of them with the model's generator and passes it to
# ``apply_to_lineage``. Each rule below only stores its parameters and calls
# the matching model primitive, so the model stays the single source of truth.

from __future__ import annotations

from typing import TYPE_CHECKING

from phyloom.simulator.net import LineageEventRule
from phyloom_ct.model import CTModel

if TYPE_CHECKING:
    from phyloom.types import NodeID


class Transmission(LineageEventRule[CTModel]):
    """Transmission event that replaces one active lineage with a continuing parent and a new child.

    Args:
        parent_state: Optional state restricting the eligible transmitting
            individuals.
        child_state: State of the newly infected individual. If omitted, it
            inherits the transmitting individual's state.
        new_parent_state: State of the transmitting individual after the
            transmission. If omitted, it keeps its state.
    """

    def __init__(
        self,
        parent_state: str | None = None,
        child_state: str | None = None,
        new_parent_state: str | None = None,
    ):
        super().__init__(parent_state)
        self._child_state = child_state
        self._new_parent_state = new_parent_state

    def apply_to_lineage(self, model: CTModel, lineage: NodeID):
        """Apply a transmission from the selected lineage."""
        model.transmission(lineage, self._child_state, self._new_parent_state)


class Migration(LineageEventRule[CTModel]):
    """Migration event that replaces one active lineage with a continuing child.

    Args:
        source_state: State of the eligible individuals.
        target_state: State of the individual after the change.
    """

    def __init__(self, source_state: str, target_state: str):
        super().__init__(source_state)
        self._target_state = target_state

    def apply_to_lineage(self, model: CTModel, lineage: NodeID):
        """Move the selected lineage to the target state."""
        model.migration(lineage, self._target_state)


class Recovery(LineageEventRule[CTModel]):
    """Recovery event that finalizes one active lineage, optionally sampling it.

    Args:
        state: Optional state restricting the eligible individuals.
        sample: Whether recovered individuals are sampled, and their contacts
            traced.
    """

    def __init__(self, state: str | None = None, *, sample: bool = False):
        super().__init__(state)
        self._sample = sample

    def apply_to_lineage(self, model: CTModel, lineage: NodeID):
        """Remove the selected lineage, sampling it if configured."""
        model.recovery(lineage, sample=self._sample)
