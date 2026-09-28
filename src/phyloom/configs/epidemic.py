"""Configuration models and event rules for compartmental epidemic simulations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from phyloom.configs.core import (
    MODEL_REGISTRY,
    EventCfg,
    EventRuleCfg,
    ModelCfgBase,
    ScheduledEventCfg,
)
from phyloom.configs.roots import IntCfg, StrCfg
from phyloom.configs.utils import contextualize_optional
from phyloom.simulator.epidemic import (
    EpidemicModel,
    Flow,
    Infection,
    Migration,
    Recovery,
)
from phyloom.utils import Registry

if TYPE_CHECKING:
    from typing import TypeAlias

    from phyloom.types import Context

#: Registry of concrete epidemic event-rule configurations keyed by their ``spec`` value.
#: It also supplies the validator used by :type:`EpidemicEventRuleCfg`.
EPIDEMIC_EVENT_RULE_REGISTRY: Registry[EventRuleCfg[EpidemicModel]] = Registry(
    "Epidemic event rule", EventRuleCfg[EpidemicModel]
)

#: Epidemic event-rule configuration type resolved by
#: :data:`EPIDEMIC_EVENT_RULE_REGISTRY`.
#: Alias for :obj:`~typing.Annotated`\[
#: :class:`~phyloom.configs.core.EventRuleCfg`,
#: :attr:`EPIDEMIC_EVENT_RULE_REGISTRY.validator
#: <phyloom.utils.Registry.validator>`\].
EpidemicEventRuleCfg: TypeAlias = Annotated[
    EventRuleCfg[EpidemicModel], EPIDEMIC_EVENT_RULE_REGISTRY.validator
]


@EPIDEMIC_EVENT_RULE_REGISTRY.register("infection")
class InfectionCfg(EventRuleCfg[EpidemicModel]):
    """Configuration for an :class:`~phyloom.simulator.epidemic.Infection` event
    that replaces one active lineage with two descendants and decrements a pool.

    Registered under ``"infection"`` in
    :data:`EPIDEMIC_EVENT_RULE_REGISTRY`.

    Args:
        recipient_pool: Pool from which the infected individual is removed.
        source_state: Optional state used to restrict eligible source
            lineages.
        child_states: Optional pair of states assigned to the descendant
            lineages. A ``None`` entry inherits the parent's state.
    """

    recipient_pool: StrCfg
    source_state: StrCfg | None = None
    child_states: tuple[StrCfg | None, StrCfg | None] = (None, None)

    def contextualize(self, context: Context) -> Infection:
        """Build the :class:`~phyloom.simulator.epidemic.Infection` event rule from materialized context values."""
        child_state1, child_state2 = self.child_states
        return Infection(
            recipient_pool=self.recipient_pool.contextualize(context),
            source_state=contextualize_optional(self.source_state, context),
            child_states=(
                contextualize_optional(child_state1, context),
                contextualize_optional(child_state2, context),
            ),
        )


@EPIDEMIC_EVENT_RULE_REGISTRY.register("recovery")
class RecoveryCfg(EventRuleCfg[EpidemicModel]):
    """Configuration for a :class:`~phyloom.simulator.epidemic.Recovery` event
    that finalizes a lineage and increments a pool.

    Registered under ``"recovery"`` in
    :data:`EPIDEMIC_EVENT_RULE_REGISTRY`.

    Args:
        destination_pool: Pool that receives the recovered individual.
        source_state: Optional state restricting eligible lineages.
        sample: Whether to record the finalized lineage as a sample.
    """

    destination_pool: StrCfg
    source_state: StrCfg | None = None
    sample: bool = False

    def contextualize(self, context: Context) -> Recovery:
        """Build the :class:`~phyloom.simulator.epidemic.Recovery` event rule from materialized context values."""
        return Recovery(
            destination_pool=self.destination_pool.contextualize(context),
            source_state=contextualize_optional(self.source_state, context),
            sample=self.sample,
        )


@EPIDEMIC_EVENT_RULE_REGISTRY.register("migration")
class MigrationCfg(EventRuleCfg[EpidemicModel]):
    """Configuration for a :class:`~phyloom.simulator.epidemic.Migration` event
    that replaces one active lineage with a continuing child.

    Registered under ``"migration"`` in
    :data:`EPIDEMIC_EVENT_RULE_REGISTRY`.

    Args:
        source_state: State restricting eligible parent lineages.
        target_state: State assigned to the child lineage.
    """

    source_state: StrCfg
    target_state: StrCfg

    def contextualize(self, context: Context) -> Migration:
        """Build the :class:`~phyloom.simulator.epidemic.Migration` event rule from materialized context values."""
        return Migration(
            source_state=self.source_state.contextualize(context),
            target_state=self.target_state.contextualize(context),
        )


@EPIDEMIC_EVENT_RULE_REGISTRY.register("flow")
class FlowCfg(EventRuleCfg[EpidemicModel]):
    """Configuration for a :class:`~phyloom.simulator.epidemic.Flow` event that
    moves one individual from a source pool to a destination pool.

    Registered under ``"flow"`` in :data:`EPIDEMIC_EVENT_RULE_REGISTRY`.

    Args:
        source_pool: Pool to decrement.
        destination_pool: Pool to increment.
    """

    source_pool: StrCfg
    destination_pool: StrCfg

    def contextualize(self, context: Context) -> Flow:
        """Build the :class:`~phyloom.simulator.epidemic.Flow` event rule from materialized context values."""
        return Flow(
            source_pool=self.source_pool.contextualize(context),
            destination_pool=self.destination_pool.contextualize(context),
        )


@MODEL_REGISTRY.register("epidemic")
class EpidemicModelCfg(ModelCfgBase):
    """Configuration for a :class:`~phyloom.simulator.epidemic.EpidemicModel`.

    Registered under ``"epidemic"`` in :data:`~phyloom.configs.core.MODEL_REGISTRY`.

    Each event selects its rule by ``spec`` from :data:`EPIDEMIC_EVENT_RULE_REGISTRY`.
    To add an event rule, implement the runtime
    :class:`~phyloom.simulator.core.EventRule`, subclass
    :class:`~phyloom.configs.core.EventRuleCfg`, implement ``contextualize``,
    and register the class. Rules acting on one or two active lineages can
    build on :class:`~phyloom.simulator.net.LineageEventRule` or
    :class:`~phyloom.simulator.net.LineagePairEventRule`. Rules whose
    opportunities depend on pool counts, such as
    :class:`~phyloom.simulator.epidemic.Infection`, implement
    ``opportunities`` and ``apply`` directly.

    .. code-block:: python

       class MyEventRule(LineageEventRule[EpidemicModel]):
          def apply_to_lineage(self, model: EpidemicModel, lineage: NodeID):
             ...

       @EPIDEMIC_EVENT_RULE_REGISTRY.register("my-event-rule")
       class MyEventRuleCfg(EventRuleCfg[EpidemicModel]):
          def contextualize(self, context: Context) -> MyEventRule:
             return MyEventRule()

    Once the module defining the configuration has been imported, the rule
    can be selected with ``spec: "my-event-rule"`` alongside the built-in
    rules:

    .. code-block:: yaml

       model:
          spec: "epidemic"
          init_state: "I"
          init_pools:
             S: 1000
          events:
             - rule:
                  spec: "infection"
                  recipient_pool: "S"
               hazard:
                  spec: "constant"
                  rate: 0.001
             - rule:
                  spec: "recovery"
                  destination_pool: "R"
                  sample: true
               hazard:
                  spec: "constant"
                  rate: 0.5
             - rule:
                  spec: "my-event-rule"
               hazard:
                  spec: "constant"
                  rate: 0.1

    Args:
        init_state: State assigned to the initial infectious lineage.
        init_pools: Initial non-negative count for each population pool.
        events: Stochastic events governing continuous-time state transitions.
        schedule: Deterministic actions executed at configured simulated
            times. Actions scheduled for the same time are shuffled before
            execution.
    """

    init_state: StrCfg
    init_pools: dict[str, IntCfg]
    events: tuple[EventCfg[EpidemicEventRuleCfg], ...] = ()
    schedule: tuple[ScheduledEventCfg, ...] = ()

    def contextualize(self, context: Context) -> EpidemicModel:
        """Build the :class:`~phyloom.simulator.epidemic.EpidemicModel` from materialized context values."""
        return EpidemicModel(
            init_state=self.init_state.contextualize(context),
            init_pools={
                pool: count.contextualize(context)
                for pool, count in self.init_pools.items()
            },
            events=[event.contextualize(context) for event in self.events],
            schedule=[i for e in self.schedule for i in e.contextualize(context)],
        )
