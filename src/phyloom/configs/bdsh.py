"""Configuration models and event rules for BDSH simulations."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated

from phyloom.configs.core import (
    MODEL_REGISTRY,
    EventCfg,
    EventRuleCfg,
    ModelCfgBase,
    ScheduledEventCfg,
)
from phyloom.configs.roots import StrCfg, StrPairCfg
from phyloom.configs.utils import contextualize_optional
from phyloom.simulator.bdsh import (
    LDH,
    LGH,
    LNH,
    BDSHModel,
    Birth,
    Death,
    Migration,
    Sampling,
)
from phyloom.utils import Registry

if TYPE_CHECKING:
    from typing import TypeAlias

    from phyloom.types import Context

#: Registry of concrete BDSH event-rule configurations keyed by their ``spec`` value.
#: It also supplies the validator used by :type:`BDSHEventRuleCfg`.
BDSH_EVENT_RULE_REGISTRY: Registry[EventRuleCfg[BDSHModel]] = Registry(
    "BDSH event rule", EventRuleCfg[BDSHModel]
)

#: BDSH event-rule configuration type resolved by :data:`BDSH_EVENT_RULE_REGISTRY`.
#: Alias for :obj:`~typing.Annotated`\[
#: :class:`~phyloom.configs.core.EventRuleCfg`,
#: :attr:`BDSH_EVENT_RULE_REGISTRY.validator
#: <phyloom.utils.Registry.validator>`\].
BDSHEventRuleCfg: TypeAlias = Annotated[
    EventRuleCfg[BDSHModel], BDSH_EVENT_RULE_REGISTRY.validator
]


@BDSH_EVENT_RULE_REGISTRY.register("birth")
class BirthCfg(EventRuleCfg[BDSHModel]):
    """Configuration for a :class:`~phyloom.simulator.bdsh.Birth` event that
    replaces one active lineage with two descendants.

    Registered under ``"birth"`` in :data:`BDSH_EVENT_RULE_REGISTRY`.

    Args:
        parent_state: Optional state restricting eligible parent lineages.
        child_states: Optional pair of states assigned to the descendant lineages.
            A ``None`` entry inherits the parent's state.
    """

    parent_state: StrCfg | None = None
    child_states: tuple[StrCfg | None, StrCfg | None] = (None, None)

    def contextualize(self, context: Context) -> Birth:
        """Build the :class:`~phyloom.simulator.bdsh.Birth` event rule from materialized context values."""
        child_state1, child_state2 = self.child_states
        return Birth(
            parent_state=contextualize_optional(self.parent_state, context),
            child_states=(
                contextualize_optional(child_state1, context),
                contextualize_optional(child_state2, context),
            ),
        )


@BDSH_EVENT_RULE_REGISTRY.register("death")
class DeathCfg(EventRuleCfg[BDSHModel]):
    """Configuration for a :class:`~phyloom.simulator.bdsh.Death` event that
    finalizes one active lineage without sampling it.

    Registered under ``"death"`` in :data:`BDSH_EVENT_RULE_REGISTRY`.

    Args:
        state: Optional state restricting eligible lineages.
    """

    state: StrCfg | None = None

    def contextualize(self, context: Context) -> Death:
        """Build the :class:`~phyloom.simulator.bdsh.Death` event rule from materialized context values."""
        return Death(state=contextualize_optional(self.state, context))


@BDSH_EVENT_RULE_REGISTRY.register("migration")
class MigrationCfg(EventRuleCfg[BDSHModel]):
    """Configuration for a :class:`~phyloom.simulator.bdsh.Migration` event
    that replaces one active lineage with a continuing child.

    Registered under ``"migration"`` in :data:`BDSH_EVENT_RULE_REGISTRY`.

    Args:
        source_state: State restricting eligible parent lineages.
        target_state: State assigned to the child lineage.
    """

    source_state: StrCfg
    target_state: StrCfg

    def contextualize(self, context: Context) -> Migration:
        """Build the :class:`~phyloom.simulator.bdsh.Migration` event rule from materialized context values."""
        return Migration(
            source_state=self.source_state.contextualize(context),
            target_state=self.target_state.contextualize(context),
        )


@BDSH_EVENT_RULE_REGISTRY.register("sampling")
class SamplingCfg(EventRuleCfg[BDSHModel]):
    """Configuration for a :class:`~phyloom.simulator.bdsh.Sampling` event
    that records one eligible active lineage.

    Registered under ``"sampling"`` in :data:`BDSH_EVENT_RULE_REGISTRY`.

    Args:
        state: Optional state restricting eligible lineages.
        removal: Whether to end the sampled lineage. If ``False``, the lineage
            first branches; one descendant is recorded as the
            sample at the current time, and the other remains active.
    """

    removal: bool
    state: StrCfg | None = None

    def contextualize(self, context: Context) -> Sampling:
        """Build the :class:`~phyloom.simulator.bdsh.Sampling` event rule from materialized context values."""
        return Sampling(
            removal=self.removal, state=contextualize_optional(self.state, context)
        )


@BDSH_EVENT_RULE_REGISTRY.register("ldh")
class LDHCfg(EventRuleCfg[BDSHModel]):
    """Configuration for a :class:`~phyloom.simulator.bdsh.LDH`
    (lineage-degenerative hybridization) event that
    replaces two active lineages with one hybrid child.

    Registered under ``"ldh"`` in :data:`BDSH_EVENT_RULE_REGISTRY`.

    Args:
        parent_states: Optional pair of states restricting the two parent lineages.
        hybrid_state: Optional state assigned to the hybrid child. If omitted,
            the parents must share the same state, which the child inherits.
    """

    parent_states: StrPairCfg | None = None
    hybrid_state: StrCfg | None = None

    def contextualize(self, context: Context) -> LDH:
        """Build the :class:`~phyloom.simulator.bdsh.LDH` event rule from materialized context values."""
        return LDH(
            parent_states=contextualize_optional(self.parent_states, context),
            hybrid_state=contextualize_optional(self.hybrid_state, context),
        )


@BDSH_EVENT_RULE_REGISTRY.register("lnh")
class LNHCfg(EventRuleCfg[BDSHModel]):
    """Configuration for a :class:`~phyloom.simulator.bdsh.LNH`
    (lineage-neutral hybridization) event.

    Registered under ``"lnh"`` in :data:`BDSH_EVENT_RULE_REGISTRY`.

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

    continuing_parent_state: StrCfg | None = None
    terminating_parent_state: StrCfg | None = None
    new_parent_state: StrCfg | None = None
    hybrid_state: StrCfg | None = None

    def contextualize(self, context: Context) -> LNH:
        """Build the :class:`~phyloom.simulator.bdsh.LNH` event rule from materialized context values."""
        return LNH(
            continuing_parent_state=contextualize_optional(
                self.continuing_parent_state, context
            ),
            terminating_parent_state=contextualize_optional(
                self.terminating_parent_state, context
            ),
            new_parent_state=contextualize_optional(self.new_parent_state, context),
            hybrid_state=contextualize_optional(self.hybrid_state, context),
        )


@BDSH_EVENT_RULE_REGISTRY.register("lgh")
class LGHCfg(EventRuleCfg[BDSHModel]):
    """Configuration for a :class:`~phyloom.simulator.bdsh.LGH`
    (lineage-generative hybridization) event.

    Registered under ``"lgh"`` in :data:`BDSH_EVENT_RULE_REGISTRY`.

    Args:
        parent_states: Optional pair of states restricting the two parent lineages.
        hybrid_state: Optional state assigned to the resulting hybrid lineage.
            If omitted, the parents must share the same state, which the
            child inherits.
        new_parent_states: Optional pair of states assigned to the continuing
            parent lineages, in the same order as ``parent_states``. A ``None``
            entry inherits the parent's state.
    """

    parent_states: StrPairCfg | None = None
    hybrid_state: StrCfg | None = None
    new_parent_states: tuple[StrCfg | None, StrCfg | None] = (None, None)

    def contextualize(self, context: Context) -> LGH:
        """Build the :class:`~phyloom.simulator.bdsh.LGH` event rule from materialized context values."""
        new_parent_state1, new_parent_state2 = self.new_parent_states
        return LGH(
            parent_states=contextualize_optional(self.parent_states, context),
            hybrid_state=contextualize_optional(self.hybrid_state, context),
            new_parent_states=(
                contextualize_optional(new_parent_state1, context),
                contextualize_optional(new_parent_state2, context),
            ),
        )


@MODEL_REGISTRY.register("bdsh")
class BDSHModelCfg(ModelCfgBase):
    """Configuration for a :class:`~phyloom.simulator.bdsh.BDSHModel`.

    Registered under ``"bdsh"`` in :data:`~phyloom.configs.core.MODEL_REGISTRY`.

    Each event selects its rule by ``spec`` from :data:`BDSH_EVENT_RULE_REGISTRY`.
    To add an event rule, implement the runtime
    :class:`~phyloom.simulator.core.EventRule`, subclass
    :class:`~phyloom.configs.core.EventRuleCfg`, implement ``contextualize``,
    and register the class. Rules acting on one or two active lineages can
    build on :class:`~phyloom.simulator.net.LineageEventRule` or
    :class:`~phyloom.simulator.net.LineagePairEventRule`.

    .. code-block:: python

       class MyEventRule(LineageEventRule[BDSHModel]):
          def apply_to_lineage(self, model: BDSHModel, lineage: NodeID):
             ...

       @BDSH_EVENT_RULE_REGISTRY.register("my-event-rule")
       class MyEventRuleCfg(EventRuleCfg[BDSHModel]):
          def contextualize(self, context: Context) -> MyEventRule:
             return MyEventRule()

    Once the module defining the configuration has been imported, the rule
    can be selected with ``spec: "my-event-rule"`` alongside the built-in
    rules:

    .. code-block:: yaml

       model:
          spec: "bdsh"
          init_state: "I"
          events:
             - rule:
                  spec: "birth"
               hazard:
                  spec: "constant"
                  rate: 1.0
             - rule:
                  spec: "sampling"
                  removal: true
               hazard:
                  spec: "constant"
                  rate: 0.5
             - rule:
                  spec: "my-event-rule"
               hazard:
                  spec: "constant"
                  rate: 0.1

    Args:
        init_state: State assigned to the initial active lineage.
        events: Stochastic events governing continuous-time state transitions.
        schedule: Deterministic actions executed at configured simulated
            times. Actions scheduled for the same time are shuffled before
            execution.
    """

    init_state: StrCfg
    events: tuple[EventCfg[BDSHEventRuleCfg], ...] = ()
    schedule: tuple[ScheduledEventCfg, ...] = ()

    def contextualize(self, context: Context) -> BDSHModel:
        """Build the :class:`~phyloom.simulator.bdsh.BDSHModel` from materialized context values."""
        return BDSHModel(
            init_state=self.init_state.contextualize(context),
            events=[event.contextualize(context) for event in self.events],
            schedule=[i for e in self.schedule for i in e.contextualize(context)],
        )
