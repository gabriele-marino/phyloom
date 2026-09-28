"""Core configuration types and registries for simulator models and events."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Annotated, Any, Generic, TypeAlias, TypeVar

from pydantic import BaseModel, ConfigDict

from phyloom.configs.hazards import HazardCfg
from phyloom.configs.roots import (
    FloatSequenceCfg,
    ModelActionCfg,
    ModelNonNegativeFloatCfg,
)
from phyloom.configs.utils import contextualize_optional
from phyloom.simulator.core import Event, Model, ModelT_contra
from phyloom.utils import Registry

if TYPE_CHECKING:
    from collections.abc import Callable

    from phyloom.simulator.core import EventRule, ModelT
    from phyloom.types import Context

RuleCfgT_co = TypeVar("RuleCfgT_co", bound="EventRuleCfg[Any]", covariant=True)


class EventRuleCfg(ABC, BaseModel, Generic[ModelT_contra]):
    """Base configuration for a model-specific :class:`~phyloom.simulator.core.EventRule`.

    An event-rule configuration declares the parameters of an event rule
    accepted in configuration data, and builds the runtime rule from them
    in :meth:`contextualize`.

    Event rules are specific to a model type, so concrete configurations are
    registered in that model's event-rule :class:`~phyloom.utils.Registry`
    rather than in a global one. To add an event rule:

    1. implement the runtime rule, a :class:`~phyloom.simulator.core.EventRule`
       providing ``opportunities`` and ``apply`` for the target model;
    2. subclass :class:`EventRuleCfg`, parametrized by the target model type,
       and declare the rule's parameters as fields;
    3. implement :meth:`contextualize` to resolve those fields and return a
       new runtime rule; and
    4. register the class under a unique key in the target model's event-rule
       registry.

    .. code-block:: python

       from phyloom.configs.core import EventRuleCfg
       from phyloom.configs.roots import StrCfg
       from phyloom.simulator.core import EventRule
       from phyloom.types import Context

       class MyEventRule(EventRule[MyModel]):
          def __init__(self, param: str):
             self._param = param

          def opportunities(self, model: MyModel) -> int:
             ...

          def apply(self, model: MyModel) -> None:
             ...

       @MY_MODEL_EVENT_RULE_REGISTRY.register("my-event-rule")
       class MyEventRuleCfg(EventRuleCfg[MyModel]):
          param: StrCfg

          def contextualize(self, context: Context) -> MyEventRule:
             return MyEventRule(self.param.contextualize(context))

    Here ``MyModel`` stands for the target model type and
    ``MY_MODEL_EVENT_RULE_REGISTRY`` for its event-rule registry. Once the
    module defining the configuration has been imported, the rule can be
    selected in an event of that model with ``spec: "my-event-rule"`` and
    combined with any hazard:

    .. code-block:: yaml

       model:
          spec: "my-model"
          events:
             - rule:
                  spec: "my-event-rule"
                  param: "..."
               hazard:
                  spec: "constant"
                  rate: 0.1
    """

    model_config = ConfigDict(extra="forbid")

    @abstractmethod
    def contextualize(self, context: Context) -> EventRule[ModelT_contra]:
        """Build the simulator event rule from materialized context values."""


class EventCfg(BaseModel, Generic[RuleCfgT_co]):
    """Configuration for a model-specific :class:`~phyloom.simulator.core.Event`.

    Concrete model configurations specialize it with their own
    registry-backed rule type.

    Args:
        rule: Event-rule configuration that determines which state transitions
            are eligible and how one is applied.
        hazard: Time-dependent per-opportunity hazard used to sample firing
            times.
        rate_multiplier: Optional model expression that scales the event's
            overall rate based on the current model state. It must return a
            non-negative numeric multiplier; zero disables the event.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    rule: RuleCfgT_co
    hazard: HazardCfg
    rate_multiplier: ModelNonNegativeFloatCfg | None = None

    def contextualize(
        self: EventCfg[EventRuleCfg[ModelT]], context: Context
    ) -> Event[ModelT]:
        """Build the :class:`~phyloom.simulator.core.Event` from materialized context values."""
        return Event(
            self.rule.contextualize(context),
            self.hazard.contextualize(context),
            rate_multiplier=contextualize_optional(self.rate_multiplier, context),
        )


class ScheduledEventCfg(BaseModel):
    """Configuration for an action executed at one or more fixed times.

    Args:
        action: Model expression evaluated at each scheduled time.
        times: Non-negative simulated times at which to evaluate the action.
    """

    model_config = ConfigDict(extra="forbid")

    action: ModelActionCfg
    times: FloatSequenceCfg

    def contextualize(
        self, context: Context
    ) -> list[tuple[float, Callable[[Any], None]]]:
        """Build one ``(time, action)`` pair per scheduled time from materialized context values."""
        times = self.times.contextualize(context)
        if any(t < 0 for t in times):
            raise ValueError("Scheduled event times must be non-negative.")
        return [(t, self.action.contextualize(context)) for t in times]


class ModelCfgBase(ABC, BaseModel):
    """Base configuration for a :class:`~phyloom.simulator.core.Model`.

    A model configuration declares the model parameters accepted in
    configuration data, together with its ``events`` and ``schedule``,
    and builds a new runtime model from them in :meth:`contextualize`.
    Concrete configurations are registered in :data:`MODEL_REGISTRY`
    under a unique key and are selected by the ``spec`` field in
    configuration data.

    A complete model extension has four pieces:

    * a :class:`~phyloom.simulator.core.Model` subclass implementing the
      model-specific state and operations;
    * one or more :class:`~phyloom.simulator.core.EventRule` implementations
      and their :class:`EventRuleCfg` configurations;
    * an event-rule :class:`~phyloom.utils.Registry` for those
      configurations, together with an :obj:`~typing.Annotated` alias that
      attaches the registry's :attr:`~phyloom.utils.Registry.validator`, so
      that each :class:`EventCfg` selects its rule by ``spec``; and
    * a registered :class:`ModelCfgBase` subclass that contextualizes the
      model parameters, events, and scheduled actions.

    .. code-block:: python

       from typing import Annotated, TypeAlias

       from phyloom.configs.core import (
          MODEL_REGISTRY,
          EventCfg,
          EventRuleCfg,
          ModelCfgBase,
          ScheduledEventCfg,
       )
       from phyloom.configs.roots import FloatCfg
       from phyloom.simulator.core import Model
       from phyloom.types import Context
       from phyloom.utils import Registry

       class MyModel(Model):
          def __init__(self, param: float, events=(), schedule=()):
             super().__init__(events, schedule)
             ...

       MY_MODEL_EVENT_RULE_REGISTRY: Registry[EventRuleCfg[MyModel]] = Registry(
          "My model event rule", EventRuleCfg[MyModel]
       )
       MyModelEventRuleCfg: TypeAlias = Annotated[
          EventRuleCfg[MyModel], MY_MODEL_EVENT_RULE_REGISTRY.validator
       ]

       # Register event-rule configurations in MY_MODEL_EVENT_RULE_REGISTRY,
       # as described in EventRuleCfg.

       @MODEL_REGISTRY.register("my-model")
       class MyModelCfg(ModelCfgBase):
          param: FloatCfg
          events: tuple[EventCfg[MyModelEventRuleCfg], ...] = ()
          schedule: tuple[ScheduledEventCfg, ...] = ()

          def contextualize(self, context: Context) -> MyModel:
             return MyModel(
                self.param.contextualize(context),
                events=[event.contextualize(context) for event in self.events],
                schedule=[
                   item
                   for entry in self.schedule
                   for item in entry.contextualize(context)
                ],
             )

    Once the module defining the configuration has been imported, the model
    can be selected in configuration data with ``spec: "my-model"``:

    .. code-block:: yaml

       model:
          spec: "my-model"
          param: 0.5
          events:
             - rule:
                  spec: "my-event-rule"
               hazard:
                  spec: "constant"
                  rate: 0.1
          schedule:
             - times: [10.0]
               action: "..."
    """

    model_config = ConfigDict(extra="forbid")

    @abstractmethod
    def contextualize(self, context: Context) -> Model:
        """Build a simulator model from materialized context values."""


#: Registry of concrete model configurations keyed by their ``spec`` value.
#: It also supplies the validator used by :type:`ModelCfg`.
MODEL_REGISTRY: Registry[ModelCfgBase] = Registry("Model", ModelCfgBase)

#: Model configuration type resolved by :data:`MODEL_REGISTRY`.
#: Alias for :obj:`~typing.Annotated`\[
#: :class:`~phyloom.configs.core.ModelCfgBase`,
#: :attr:`MODEL_REGISTRY.validator
#: <phyloom.utils.Registry.validator>`\].
ModelCfg: TypeAlias = Annotated[ModelCfgBase, MODEL_REGISTRY.validator]
