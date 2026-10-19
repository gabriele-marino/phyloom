from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from pydantic import RootModel

from phyloom.configs.roots._source import NumPyExpressionCfg
from phyloom.configs.roots.typeguards import FLOAT_SEQUENCE_TG, FLOAT_TG

if TYPE_CHECKING:
    from phyloom.types import Context


class FloatCfg(RootModel[NumPyExpressionCfg]):
    """Configuration for a float-valued NumPy expression."""

    root: NumPyExpressionCfg

    def contextualize(self, context: Context) -> float:
        """Evaluate the expression to a float from materialized context values."""
        return self.root.contextualize(context, typeguard=FLOAT_TG)


class FloatSequenceCfg(RootModel[NumPyExpressionCfg | Sequence[FloatCfg]]):
    """Configuration for a sequence of floats.

    The sequence is given either as a list of float-valued expressions or as a
    single NumPy expression that evaluates to a sequence of floats.
    """

    root: NumPyExpressionCfg | Sequence[FloatCfg]

    def contextualize(self, context: Context) -> Sequence[float]:
        """Evaluate the expression, or each of its elements, to a sequence of floats from materialized context values."""
        if isinstance(self.root, NumPyExpressionCfg):
            return self.root.contextualize(context, typeguard=FLOAT_SEQUENCE_TG)
        return [x.contextualize(context) for x in self.root]
