from __future__ import annotations

from typing import TYPE_CHECKING

from phyloom.simulator.epidemic._model import EpidemicModel
from phyloom.simulator.net import LineageEventRule

if TYPE_CHECKING:
    from phyloom.types import NodeID


class Infection:
    """Infection event that replaces one active lineage with two descendants and decrements a pool.

    The number of infection opportunities is the product of the number of
    eligible source lineages and the number of individuals in
    ``recipient_pool``. When an opportunity is selected, one eligible source
    lineage is chosen uniformly, one individual is removed from the recipient
    pool, and the lineage is replaced by two descendants.

    Args:
        recipient_pool: Pool from which the infected individual is removed.
        source_state: Optional state used to restrict eligible source
            lineages.
        child_states: Optional pair of states assigned to the descendant
            lineages. A ``None`` entry inherits the parent's state.
    """

    def __init__(
        self,
        recipient_pool: str,
        source_state: str | None = None,
        child_states: tuple[str | None, str | None] = (None, None),
    ):
        self._recipient_pool = recipient_pool
        self._source_state = source_state
        self._child_states = child_states

    def opportunities(self, model: EpidemicModel):
        """Count the number of infection opportunities in the model."""
        return (
            model.count_current_lineages(self._source_state)
            * model.pools[self._recipient_pool]
        )

    def apply(self, model: EpidemicModel):
        """Select one infection opportunity and apply it to the model."""
        (lineage,) = model.draw_current_lineages(self._source_state)
        model.infection(lineage, self._recipient_pool, child_states=self._child_states)


class Recovery(LineageEventRule[EpidemicModel]):
    """Recovery event that finalizes a lineage and increments a pool.

    Args:
        destination_pool: Pool receiving the recovered individual.
        source_state: Optional state restricting eligible lineages.
        sample: Whether to record the finalized lineage as a sample.
    """

    def __init__(
        self,
        destination_pool: str,
        source_state: str | None = None,
        *,
        sample: bool = False,
    ):
        super().__init__(source_state)
        self._destination_pool = destination_pool
        self._sample = sample

    def apply_to_lineage(self, model: EpidemicModel, lineage: NodeID):
        """Finalize the selected lineage and increment the destination pool."""
        model.recovery(lineage, self._destination_pool, sample=self._sample)


class Migration(LineageEventRule[EpidemicModel]):
    """State-change event that replaces one active lineage with a continuing child.

    Args:
        source_state: State restricting eligible parent lineages.
        target_state: State assigned to the child lineage.
    """

    def __init__(self, source_state: str, target_state: str):
        super().__init__(source_state)
        self._target_state = target_state

    def apply_to_lineage(self, model: EpidemicModel, lineage: NodeID):
        """Replace the selected lineage with a continuing child in the target state."""
        model.migration(lineage, self._target_state)


class Flow:
    """Pool-flow event that moves one individual from a source pool to a destination pool.

    There is one opportunity for every individual in ``source_pool``. ``Flow``
    does not affect lineages, and only modifies the counts of individuals
    in the source and destination pools.

    Args:
        source_pool: Pool to decrement.
        destination_pool: Pool to increment.
    """

    def __init__(self, source_pool: str, destination_pool: str):
        self._source_pool = source_pool
        self._destination_pool = destination_pool

    def opportunities(self, model: EpidemicModel):
        """Count the number of individuals currently in ``source_pool``."""
        return model.pools[self._source_pool]

    def apply(self, model: EpidemicModel):
        """Move one individual from ``source_pool`` to ``destination_pool``."""
        model.flow(self._source_pool, self._destination_pool)
