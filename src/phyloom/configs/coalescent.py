"""Configuration models and event rules for coalescent simulations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from phyloom.configs.core import (
    MODEL_REGISTRY,
    EventCfg,
    EventRuleCfg,
    ModelCfgBase,
    ScheduledEventCfg,
)
from phyloom.configs.roots import IntCfg, StrCfg, StrPairCfg
from phyloom.configs.utils import contextualize_optional
from phyloom.simulator.coalescent import Coalesce, CoalescentModel, Retrace
from phyloom.utils import Registry

if TYPE_CHECKING:
    from typing import TypeAlias

    from phyloom.types import Context

#: Registry of concrete coalescent event-rule configurations keyed by their ``spec`` value.
#: It also supplies the validator used by :type:`CoalescentEventRuleCfg`.
COALESCENT_EVENT_RULE_REGISTRY: Registry[EventRuleCfg[CoalescentModel]] = Registry(
    "Coalescent event rule", EventRuleCfg[CoalescentModel]
)

#: Coalescent event-rule configuration type resolved by
#: :data:`COALESCENT_EVENT_RULE_REGISTRY`.
#: Alias for :obj:`~typing.Annotated`\[
#: :class:`~phyloom.configs.core.EventRuleCfg`,
#: :attr:`COALESCENT_EVENT_RULE_REGISTRY.validator
#: <phyloom.utils.Registry.validator>`\].
CoalescentEventRuleCfg: TypeAlias = Annotated[
    EventRuleCfg[CoalescentModel], COALESCENT_EVENT_RULE_REGISTRY.validator
]


@COALESCENT_EVENT_RULE_REGISTRY.register("retrace")
class RetraceCfg(EventRuleCfg[CoalescentModel]):
    """Configuration for a :class:`~phyloom.simulator.coalescent.Retrace` event
    that replaces one active lineage with an ancestral parent.

    Registered under ``"retrace"`` in
    :data:`COALESCENT_EVENT_RULE_REGISTRY`.

    Args:
        ancestral_state: State assigned to the new parent.
        current_state: Optional state restricting eligible lineages.
    """

    ancestral_state: StrCfg
    current_state: StrCfg | None = None

    def contextualize(self, context: Context) -> Retrace:
        """Build the :class:`~phyloom.simulator.coalescent.Retrace` event rule from materialized context values."""
        return Retrace(
            ancestral_state=self.ancestral_state.contextualize(context),
            current_state=contextualize_optional(self.current_state, context),
        )


@COALESCENT_EVENT_RULE_REGISTRY.register("coalesce")
class CoalesceCfg(EventRuleCfg[CoalescentModel]):
    """Configuration for a :class:`~phyloom.simulator.coalescent.Coalesce` event
    that replaces two active lineages with one ancestral parent.

    Registered under ``"coalesce"`` in
    :data:`COALESCENT_EVENT_RULE_REGISTRY`.

    Args:
        current_states: Optional pair of states restricting the child pair.
        ancestral_state: Optional state assigned to the ancestral parent. If
            omitted, the child lineages must share the same state, which the
            parent inherits.
    """

    current_states: StrPairCfg | None = None
    ancestral_state: StrCfg | None = None

    def contextualize(self, context: Context) -> Coalesce:
        """Build the :class:`~phyloom.simulator.coalescent.Coalesce` event rule from materialized context values."""
        return Coalesce(
            current_states=contextualize_optional(self.current_states, context),
            ancestral_state=contextualize_optional(self.ancestral_state, context),
        )


@MODEL_REGISTRY.register("coalescent")
class CoalescentModelCfg(ModelCfgBase):
    """Configuration for a :class:`~phyloom.simulator.coalescent.CoalescentModel`.

    Registered under ``"coalescent"`` in :data:`~phyloom.configs.core.MODEL_REGISTRY`.

    Each event selects its rule by ``spec`` from :data:`COALESCENT_EVENT_RULE_REGISTRY`.
    To add an event rule, implement the runtime
    :class:`~phyloom.simulator.core.EventRule`, subclass
    :class:`~phyloom.configs.core.EventRuleCfg`, implement ``contextualize``,
    and register the class. Rules acting on one or two active lineages can
    build on :class:`~phyloom.simulator.net.LineageEventRule` or
    :class:`~phyloom.simulator.net.LineagePairEventRule`.

    .. code-block:: python

       class MyEventRule(LineageEventRule[CoalescentModel]):
          def apply_to_lineage(self, model: CoalescentModel, lineage: NodeID):
             ...

       @COALESCENT_EVENT_RULE_REGISTRY.register("my-event-rule")
       class MyEventRuleCfg(EventRuleCfg[CoalescentModel]):
          def contextualize(self, context: Context) -> MyEventRule:
             return MyEventRule()

    Once the module defining the configuration has been imported, the rule
    can be selected with ``spec: "my-event-rule"`` alongside the built-in
    rules:

    .. code-block:: yaml

       model:
          spec: "coalescent"
          init_population:
             A: 10
          events:
             - rule:
                  spec: "coalesce"
               hazard:
                  spec: "constant"
                  rate: 1.0
             - rule:
                  spec: "my-event-rule"
               hazard:
                  spec: "constant"
                  rate: 0.1

    Args:
        init_population: Positive number of initial active lineages for each
            state.
        events: Stochastic events governing continuous-time state transitions.
        schedule: Deterministic actions executed at configured simulated
            times. Actions scheduled for the same time are shuffled before
            execution.
    """

    init_population: dict[str, IntCfg]
    events: tuple[EventCfg[CoalescentEventRuleCfg], ...] = ()
    schedule: tuple[ScheduledEventCfg, ...] = ()

    def contextualize(self, context: Context) -> CoalescentModel:
        """Build the :class:`~phyloom.simulator.coalescent.CoalescentModel` from materialized context values."""
        return CoalescentModel(
            init_population={
                state: size.contextualize(context)
                for state, size in self.init_population.items()
            },
            events=[event.contextualize(context) for event in self.events],
            schedule=[i for e in self.schedule for i in e.contextualize(context)],
        )
