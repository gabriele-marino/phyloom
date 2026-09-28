"""Configuration of the contact-tracing model and its event rules."""

# This is the module named by the ``phyloom.plugins`` entry point in
# ``pyproject.toml``. Importing it registers the ``ct`` model and its event
# rules. Each configuration class declares the YAML keys of its runtime
# counterpart, and its ``contextualize`` method resolves them for one sample's
# context. The runner calls ``contextualize`` once per trial, so it always
# builds new objects.

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, TypeAlias

from phyloom.configs.core import (
    MODEL_REGISTRY,
    EventCfg,
    EventRuleCfg,
    ModelCfgBase,
    ScheduledEventCfg,
)
from phyloom.configs.roots import FloatCfg, IntCfg, StrCfg
from phyloom.configs.utils import contextualize_optional
from phyloom.utils import Registry
from phyloom_ct.events import Migration, Recovery, Transmission
from phyloom_ct.model import CTModel

if TYPE_CHECKING:
    from phyloom.simulator.core import EventRule
    from phyloom.types import Context


# Event rules are specific to a model, so the model gets its own registry of
# rule configurations rather than reusing BDSH's. BDSH rules call BDSH
# primitives directly, which CTModel inherits but which bypass its individual
# bookkeeping, and the BDSH registry would let a ``bdsh`` model select these
# rules, which need a CTModel; its keys, such as ``migration``, are also
# already taken. With a dedicated registry, YAML can use exactly the
# transitions the model supports, and anything else fails at validation.
#
# The registry's validator reads the ``spec`` key, looks up the registered
# class, and validates the remaining keys with it. Model and hazard registries
# work the same way.
CT_EVENT_RULE_REGISTRY: Registry[EventRuleCfg[CTModel]] = Registry(
    "CT event rule", EventRuleCfg[CTModel]
)
CTEventRuleCfg: TypeAlias = Annotated[
    EventRuleCfg[CTModel], CT_EVENT_RULE_REGISTRY.validator
]


@CT_EVENT_RULE_REGISTRY.register("transmission")
class TransmissionCfg(EventRuleCfg[CTModel]):
    """Configuration for a :class:`~phyloom_ct.events.Transmission` event that replaces one active lineage with a continuing parent and a new child."""

    # States are StrCfg, so YAML can write a literal (``I``) or a placeholder
    # (``"{init_state}"``). ``None`` means no state filter for ``parent_state``,
    # and no state change for ``child_state`` and ``new_parent_state``.
    parent_state: StrCfg | None = None
    child_state: StrCfg | None = None
    new_parent_state: StrCfg | None = None

    def contextualize(self, context: Context) -> EventRule[CTModel]:
        return Transmission(
            parent_state=contextualize_optional(self.parent_state, context),
            child_state=contextualize_optional(self.child_state, context),
            new_parent_state=contextualize_optional(self.new_parent_state, context),
        )


@CT_EVENT_RULE_REGISTRY.register("migration")
class MigrationCfg(EventRuleCfg[CTModel]):
    """Configuration for a :class:`~phyloom_ct.events.Migration` event that replaces one active lineage with a continuing child."""

    source_state: StrCfg
    target_state: StrCfg

    def contextualize(self, context: Context) -> EventRule[CTModel]:
        return Migration(
            source_state=self.source_state.contextualize(context),
            target_state=self.target_state.contextualize(context),
        )


@CT_EVENT_RULE_REGISTRY.register("recovery")
class RecoveryCfg(EventRuleCfg[CTModel]):
    """Configuration for a :class:`~phyloom_ct.events.Recovery` event that finalizes one active lineage, optionally sampling it."""

    # A plain bool: whether a recovery is observed is a structural choice that
    # should not depend on the context.
    state: StrCfg | None = None
    sample: bool = False

    def contextualize(self, context: Context) -> EventRule[CTModel]:
        return Recovery(
            state=contextualize_optional(self.state, context), sample=self.sample
        )


@MODEL_REGISTRY.register("ct")
class CTModelCfg(ModelCfgBase):
    """Configuration for a :class:`~phyloom_ct.model.CTModel`."""

    # Like the built-in model configurations: each ``events`` entry has a rule,
    # validated through the CT registry, a hazard, validated through the global
    # hazard registry, and an optional rate multiplier; each ``schedule`` entry
    # expands to one (time, action) pair per time, hence the flattening below.
    # The tracing parameters accept numbers or context expressions, so they are
    # FloatCfg and IntCfg rather than plain float and int.

    init_state: StrCfg
    events: tuple[EventCfg[CTEventRuleCfg], ...] = ()
    schedule: tuple[ScheduledEventCfg, ...] = ()
    notification_probability: FloatCfg = FloatCfg.model_validate(1.0)
    max_notifications: IntCfg | None = None

    def contextualize(self, context: Context) -> CTModel:
        return CTModel(
            init_state=self.init_state.contextualize(context),
            events=[event.contextualize(context) for event in self.events],
            schedule=[
                action
                for event in self.schedule
                for action in event.contextualize(context)
            ],
            notification_probability=self.notification_probability.contextualize(
                context
            ),
            max_notifications=contextualize_optional(self.max_notifications, context),
        )
