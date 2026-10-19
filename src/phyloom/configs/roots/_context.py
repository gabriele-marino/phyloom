from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field, RootModel

from phyloom.configs.roots._source import NumPyExpressionCfg
from phyloom.configs.roots._str import StrCfg

if TYPE_CHECKING:
    from numpy.random import Generator

    from phyloom.types import Context


class DistributionCfg(BaseModel):
    """Configuration for a context variable drawn from a prior distribution.

    Args:
        type: Name of the :class:`numpy.random.Generator` distribution method, such
            as ``"uniform"``, ``"lognormal"``, or ``"integers"``.
        **extra_data: Keyword arguments accepted by that NumPy distribution method.
    """

    model_config = ConfigDict(extra="allow")
    type: StrCfg
    __pydantic_extra__: dict[str, NumPyExpressionCfg] = Field(init=False)  # pyright: ignore[reportIncompatibleVariableOverride]

    def draw(self, context: Context, rng: Generator) -> object:
        """Draw a sample from the distribution, evaluating any extra data from materialized context values."""
        args = {
            name: value.contextualize(context)
            for name, value in self.__pydantic_extra__.items()
        }
        return getattr(rng, self.type.contextualize(context))(**args)


class ContextCfg(RootModel[dict[str, DistributionCfg | NumPyExpressionCfg]]):
    """Configuration for the sample-specific context variables.

    For every sample, the context is materialized into sample-specific
    parameter values: each entry is either drawn from its prior distribution
    or evaluated as an expression, such as a fixed constant or a quantity
    derived from earlier entries.
    """

    root: dict[str, DistributionCfg | NumPyExpressionCfg] = {}

    def materialize(self, rng: Generator) -> Context:
        """Materialize the sample-specific values, evaluating or drawing each entry in order."""
        values: Context = {}
        for key, value in self.root.items():
            if isinstance(value, NumPyExpressionCfg):
                values[key] = value.contextualize(values)
            else:
                values[key] = value.draw(values, rng)
        return values
