"""Configuration models for time-dependent event hazards."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Annotated

from pydantic import BaseModel, ConfigDict

from phyloom.configs.roots import (
    FloatCfg,
    FloatSequenceCfg,
    IntCfg,
    NonNegativeTimeFnCfg,
)
from phyloom.simulator.hazards import (
    ConstantHazard,
    DeltaHazard,
    ExponentialHazard,
    NumericHazard,
    SkylineHazard,
)
from phyloom.utils import Registry

if TYPE_CHECKING:
    from typing import TypeAlias

    from phyloom.simulator.hazards import Hazard
    from phyloom.types import Context


class HazardCfgBase(ABC, BaseModel):
    """Base configuration for a :class:`~phyloom.simulator.hazards.Hazard`.

    A hazard configuration declares the hazard parameters accepted in
    configuration data, and builds the runtime hazard from them in
    :meth:`contextualize`. Concrete hazard configurations are
    registered in :data:`HAZARD_REGISTRY` under a unique key and are
    selected by the ``spec`` field in configuration data. Hazards do
    not depend on the model type, so a registered hazard can be
    combined with any event rule.

    To add a hazard, implement the runtime
    :class:`~phyloom.simulator.hazards.Hazard`,
    subclass :class:`HazardCfgBase`, implement :meth:`contextualize`, and
    register the class:

    .. code-block:: python

       from phyloom.configs.hazards import HAZARD_REGISTRY, HazardCfgBase
       from phyloom.configs.roots import FloatCfg
       from phyloom.simulator.hazards import Hazard
       from phyloom.types import Context

       class MyHazard(Hazard):
          def __init__(self, param: float):
             self._param = param

          def invert(self, t0: float, threshold: float) -> float | None:
             ...

       @HAZARD_REGISTRY.register("my-hazard")
       class MyHazardCfg(HazardCfgBase):
          param: FloatCfg

          def contextualize(self, context: Context) -> MyHazard:
             return MyHazard(self.param.contextualize(context))

    Once the module defining the configuration has been imported, the hazard
    can be selected in any event with ``spec: "my-hazard"``:

    .. code-block:: yaml

       model:
          events:
             - rule:
                  spec: "..."
               hazard:
                  spec: "my-hazard"
                  param: 1.0
    """

    model_config = ConfigDict(extra="forbid")

    @abstractmethod
    def contextualize(self, context: Context) -> Hazard:
        """Build the simulator hazard from materialized context values."""


#: Registry of concrete hazard configurations keyed by their ``spec`` value.
#: It also supplies the validator used by :type:`HazardCfg`.
HAZARD_REGISTRY: Registry[HazardCfgBase] = Registry("Hazard", HazardCfgBase)

#: Hazard configuration type resolved by :data:`HAZARD_REGISTRY`.
#: Alias for :obj:`~typing.Annotated`\[
#: :class:`~phyloom.configs.hazards.HazardCfgBase`,
#: :attr:`HAZARD_REGISTRY.validator
#: <phyloom.utils.Registry.validator>`\].
HazardCfg: TypeAlias = Annotated[HazardCfgBase, HAZARD_REGISTRY.validator]


@HAZARD_REGISTRY.register("constant")
class ConstantHazardCfg(HazardCfgBase):
    """Configuration for a :class:`~phyloom.simulator.hazards.ConstantHazard`
    with a constant per-opportunity rate.

    Registered under ``"constant"`` in :data:`HAZARD_REGISTRY`.

    Args:
        rate: Positive per-opportunity event rate.
    """

    rate: FloatCfg

    def contextualize(self, context: Context) -> ConstantHazard:
        """Build the :class:`~phyloom.simulator.hazards.ConstantHazard` from materialized context values."""
        return ConstantHazard(self.rate.contextualize(context))


@HAZARD_REGISTRY.register("delta")
class DeltaHazardCfg(HazardCfgBase):
    """Configuration for a :class:`~phyloom.simulator.hazards.DeltaHazard`
    that fires immediately at a point mass.

    Registered under ``"delta"`` in :data:`HAZARD_REGISTRY`.
    """

    def contextualize(self, context: Context) -> DeltaHazard:
        """Build the :class:`~phyloom.simulator.hazards.DeltaHazard` from materialized context values."""
        return DeltaHazard()


@HAZARD_REGISTRY.register("exponential")
class ExponentialHazardCfg(HazardCfgBase):
    """Configuration for a :class:`~phyloom.simulator.hazards.ExponentialHazard`
    whose rate changes exponentially with time.

    Registered under ``"exponential"`` in :data:`HAZARD_REGISTRY`.

    Args:
        rate: Positive rate at simulated time zero.
        decay: Exponential decay or growth parameter. A positive value gives
            decay, zero gives a constant rate, and a negative value gives
            growth.
    """

    rate: FloatCfg
    decay: FloatCfg

    def contextualize(self, context: Context) -> ExponentialHazard:
        """Build the :class:`~phyloom.simulator.hazards.ExponentialHazard` from materialized context values."""
        return ExponentialHazard(
            self.rate.contextualize(context), self.decay.contextualize(context)
        )


@HAZARD_REGISTRY.register("skyline")
class SkylineHazardCfg(HazardCfgBase):
    """Configuration for a :class:`~phyloom.simulator.hazards.SkylineHazard`
    with piecewise-constant rates.

    Registered under ``"skyline"`` in :data:`HAZARD_REGISTRY`.

    Args:
        rates: Non-negative per-interval rates, ordered from earliest to latest
            interval.
        break_times: Positive, strictly increasing times separating adjacent
            intervals. Provide one fewer value than ``rates``.
    """

    rates: FloatSequenceCfg
    break_times: FloatSequenceCfg

    def contextualize(self, context: Context) -> SkylineHazard:
        """Build the :class:`~phyloom.simulator.hazards.SkylineHazard` from materialized context values."""
        return SkylineHazard(
            self.rates.contextualize(context), self.break_times.contextualize(context)
        )


@HAZARD_REGISTRY.register("numeric")
class NumericHazardCfg(HazardCfgBase):
    """Configuration for a :class:`~phyloom.simulator.hazards.NumericHazard`
    whose rate is numerically inverted over time.

    Registered under ``"numeric"`` in :data:`HAZARD_REGISTRY`.

    Args:
        rate_fn: Expression for the non-negative event rate as a function of simulated time.
        max_bracketing_steps: Maximum number of interval expansions used to
            bracket the numerical inversion.
        initial_dt: Initial interval width used when searching for a bracket.
    """

    rate_fn: NonNegativeTimeFnCfg
    max_bracketing_steps: IntCfg = IntCfg.model_validate(16)
    initial_dt: FloatCfg = FloatCfg.model_validate(1.0)

    def contextualize(self, context: Context) -> NumericHazard:
        """Build the :class:`~phyloom.simulator.hazards.NumericHazard` from materialized context values."""
        return NumericHazard(
            self.rate_fn.contextualize(context),
            max_bracketing_steps=self.max_bracketing_steps.contextualize(context),
            initial_dt=self.initial_dt.contextualize(context),
        )
