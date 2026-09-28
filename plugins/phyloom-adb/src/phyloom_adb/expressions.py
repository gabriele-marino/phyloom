"""Configuration expressions evaluated on a lineage state."""

# YAML expressions for the ADB model depend on the lineage's ``state``, which
# none of Phyloom's built-in configuration types binds, so the plugin defines
# two ExpressionCfg subclasses.
#
# An ExpressionCfg wraps one Python expression:
# * at validation, the string is compiled, so a syntax error is reported with
#   the path of the field before anything is simulated;
# * ``contextualize(context)`` returns a callable that evaluates the expression
#   with the context values, plus ``model`` and ``state``.

from __future__ import annotations

from typing import TYPE_CHECKING

from phyloom.configs.roots import ExpressionCfg
from phyloom.configs.roots.typeguards import FLOAT_TG, is_sequence

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence
    from typing import Any, TypeGuard

    from phyloom.types import Context
    from phyloom_adb.model import StrOrNonePair


class FloatStateExpression(ExpressionCfg):
    """Configuration for a non-negative float expression that can refer to a lineage's state."""

    def contextualize(self, context: Context) -> Callable[[Any, Any], float]:
        """Return a function of ``model`` and ``state`` that runs the source."""

        def func(model: Any, state: str) -> float:
            # The typeguard converts NumPy results to plain Python values and
            # checks the result before it crosses into the model, so an
            # expression that returns, say, a string fails with a clear error.
            val = self.evaluate_typed(context, FLOAT_TG, model=model, state=state)
            if val < 0:
                raise ValueError(
                    f"Expression {self.root!r} evaluated to a negative value (got {val})."
                )
            return val

        return func


def is_pair_of_str_or_none(value: object) -> TypeGuard[Sequence[str | None]]:
    """Check whether a value is a sequence of two strings or ``None`` values."""
    return (
        is_sequence(value)
        and len(value) == 2
        and all(isinstance(s, (str, type(None))) for s in value)
    )


class ChildStatesExpression(ExpressionCfg):
    """Configuration for an expression that returns the states of two child lineages."""

    # No built-in typeguard covers "two states or None values", so this expression
    # uses the untyped ``evaluate`` and performs its own check.
    def contextualize(self, context: Context) -> Callable[[Any, Any], StrOrNonePair]:
        """Return a function of ``model`` and ``state`` that runs the source."""

        def func(model: Any, state: str) -> StrOrNonePair:
            val = self.evaluate(context, model=model, state=state)
            if not is_pair_of_str_or_none(val):
                raise ValueError(
                    f"Expression {self.root!r} evaluated to an invalid value (got {val}). "
                    f"Expected a sequence of two strings or None values."
                )
            return (val[0], val[1])

        return func
