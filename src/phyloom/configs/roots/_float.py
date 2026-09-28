from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from pydantic import RootModel

from phyloom.configs.roots._source import NumPyExpressionCfg
from phyloom.configs.roots.typeguards import FLOAT_SEQUENCE_TG, FLOAT_TG

if TYPE_CHECKING:
    from phyloom.types import Context


class FloatCfg(RootModel[NumPyExpressionCfg]):
    """Configuration for a float-valued expression.

    Examples:
        Configure a context-dependent maximum simulation time.

        .. code-block:: yaml

           context:
              birth_rate: 0.1
           max_time: 100 / birth_rate
    """

    root: NumPyExpressionCfg

    def contextualize(self, context: Context) -> float:
        """Evaluate the expression to a float from materialized context values."""
        return self.root.contextualize(context, typeguard=FLOAT_TG)


class FloatSequenceCfg(RootModel[NumPyExpressionCfg | Sequence[FloatCfg]]):
    """Configuration for a sequence of float-valued expressions.

    Examples:
        Configure a context-dependent list of rates and break times.

        .. code-block:: yaml

           context:
              first_rate: 0.1
              rates: np.array([first_rate, 0.2, 0.3])
              first_time: 1.0
              break_times: [first_time, 2.0]
    """

    root: NumPyExpressionCfg | Sequence[FloatCfg]

    def contextualize(self, context: Context) -> Sequence[float]:
        """Evaluate the expression, or each of its elements, to a sequence of floats from materialized context values."""
        if isinstance(self.root, NumPyExpressionCfg):
            return self.root.contextualize(context, typeguard=FLOAT_SEQUENCE_TG)
        return [x.contextualize(context) for x in self.root]
