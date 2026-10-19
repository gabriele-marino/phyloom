"""Core configuration types and registries for simulator models and events."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Annotated, Any, Generic, TypeAlias, TypeVar

from pydantic import BaseModel, ConfigDict

from phyloom.configs.hazards import HazardCfg
from phyloom.configs.roots import (
    FloatSequenceCfg,
    ModelActionCfg,
    NonNegativeModelFnCfg,
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

    Subclasses declare the parameters of an event rule as fields and build the
    runtime rule from them in :meth:`contextualize`. Event rules act on a
    specific model type, so concrete configurations are registered in the
    event-rule :class:`~phyloom.utils.Registry` of that model.
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
    rate_multiplier: NonNegativeModelFnCfg | None = None

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
        action: Model statements run at each scheduled time.
        times: Non-negative simulated times at which to run the action.
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

    Subclasses declare the model parameters, together with the model's
    ``events`` and ``schedule``, as fields and build a new runtime model from
    them in :meth:`contextualize`. Concrete configurations are registered in
    :data:`MODEL_REGISTRY` and selected by their ``spec`` key.
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
