from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field, RootModel

from phyloom.configs.roots._source import NumPyExpressionCfg
from phyloom.configs.roots._str import StrCfg

if TYPE_CHECKING:
    from numpy.random import Generator

    from phyloom.types import Context


class DistributionCfg(BaseModel):
    """Configuration for a context variable drawn from a NumPy distribution.

    The ``type`` field selects a method on the supplied
    :class:`numpy.random.Generator`. Every additional field is evaluated and
    passed to that method as a keyword argument. These arguments can refer to
    earlier context entries and to the :mod:`numpy` module as ``np``.

    Args:
        type: Name of the :class:`numpy.random.Generator` distribution method, such
            as ``"uniform"``, ``"lognormal"``, or ``"integers"``.
        **extra_data: Arguments accepted by that NumPy distribution method.

    Examples:
        Configure a randomly-drawn context variable.

        .. code-block:: yaml

           context:
              lower_bound: 0.1
              rate:
                 type: uniform
                 low: lower_bound
                 high: lower_bound * 10
    """

    model_config = ConfigDict(extra="allow")
    type: StrCfg
    __pydantic_extra__: dict[str, NumPyExpressionCfg] = Field(init=False)  # pyright: ignore[reportIncompatibleVariableOverride]

    def draw(self, context: Context, rng: Generator) -> object:
        """Draw one value from the configured distribution, with arguments resolved from materialized context values."""
        args = {
            name: value.contextualize(context)
            for name, value in self.__pydantic_extra__.items()
        }
        return getattr(rng, self.type.contextualize(context))(**args)


class ContextCfg(RootModel[dict[str, DistributionCfg | NumPyExpressionCfg]]):
    """Configuration for the sample-specific context variables.

    The root mapping is evaluated in insertion order, so that a later
    value can depend on an earlier expression or random draw.

    Examples:
        Configure a sample-specific context with fixed constants, derived
        mathematical expressions, and random distributions that reference
        previously evaluated variables:

        .. code-block:: yaml

           context:
              generation_time: 2.5
              birth_rate: 1 / generation_time
              lower_bound:
                 type: integers
                 low: 20
                 high: 50
              initial_size:
                 type: integers
                 low: lower_bound
                 high: 250
    """

    root: dict[str, DistributionCfg | NumPyExpressionCfg] = {}

    def materialize(self, rng: Generator) -> Context:
        """Materialize the context by evaluating or drawing each entry in order."""
        values: Context = {}
        for key, value in self.root.items():
            if isinstance(value, NumPyExpressionCfg):
                values[key] = value.contextualize(values)
            else:
                values[key] = value.draw(values, rng)
        return values
