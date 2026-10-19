from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import RootModel

from phyloom.configs.roots._source import NumPyExpressionCfg
from phyloom.configs.roots.typeguards import INT_TG

if TYPE_CHECKING:
    from phyloom.types import Context


class IntCfg(RootModel[NumPyExpressionCfg]):
    """Configuration for an integer-valued NumPy expression."""

    root: NumPyExpressionCfg

    def contextualize(self, context: Context) -> int:
        """Evaluate the expression to an integer from materialized context values."""
        return self.root.contextualize(context, typeguard=INT_TG)
