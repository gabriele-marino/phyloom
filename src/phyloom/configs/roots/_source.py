from __future__ import annotations

from functools import cache
from typing import TYPE_CHECKING, ClassVar, Literal, TypeVar, overload

import numpy as np
from pydantic import ConfigDict, RootModel, field_validator

from phyloom.configs.roots.typeguards import BOOL_TG, FLOAT_TG, NamedTypeguard

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import CodeType
    from typing import Any

    from phyloom.types import Context

T = TypeVar("T")


@cache
def _compile(source: str, mode: Literal["eval", "exec"]) -> CodeType:
    try:
        return compile(source, f"<phyloom {mode}>", mode)
    except SyntaxError as exc:
        raise ValueError(f"Invalid Python {mode} source {source!r}: {exc.msg}") from exc


class _SourceCfg(RootModel[str]):
    root: str
    _MODE: ClassVar[Literal["eval", "exec"]]

    @field_validator("root")
    @classmethod
    def _check_syntax(cls, value: str) -> str:
        _compile(value, cls._MODE)
        return value

    @property
    def _code(self) -> CodeType:
        return _compile(self.root, self._MODE)

    def _namespace(self, context: Context, **bindings: object) -> dict[str, object]:
        return {**context, "np": np, **bindings}


class ExpressionCfg(_SourceCfg):
    """Base configuration for a Python expression that produces a value.

    The expression is syntax-checked during validation and evaluated later,
    during a simulation. It sees the materialized context, :mod:`numpy` as
    ``np``, and the keyword bindings passed to :meth:`evaluate` or
    :meth:`evaluate_typed`, which take precedence over context names.
    Subclasses implement ``contextualize`` to return a function that evaluates
    the expression each time it is called. The source is not sandboxed, so
    configuration input must be trusted.
    """

    _MODE: ClassVar[Literal["eval", "exec"]] = "eval"

    def evaluate(self, context: Context, **bindings: object) -> object:
        """Evaluate the expression and return its raw value."""
        return eval(self._code, self._namespace(context, **bindings))

    def evaluate_typed(
        self, context: Context, typeguard: NamedTypeguard[T], **bindings: object
    ) -> T:
        """Evaluate the expression and check its type.

        NumPy results are converted to plain Python values before the value is
        checked with ``typeguard``.
        """
        value = np.asarray(self.evaluate(context, **bindings)).tolist()
        if typeguard.fn(value):
            return value
        raise ValueError(
            f"Expression {self.root!r} evaluated to {value} of type "
            f"{type(value).__name__}, expected a {typeguard.name}."
        )


class StatementCfg(_SourceCfg):
    """Base configuration for Python statements run for their side effects.

    The statements are syntax-checked during validation and run later, during
    a simulation. They see the materialized context, :mod:`numpy` as ``np``,
    and the keyword bindings passed to :meth:`execute`, which take precedence
    over context names. Subclasses implement ``contextualize`` to return a
    function that runs the statements each time it is called. The source is
    not sandboxed, so configuration input must be trusted.
    """

    _MODE: ClassVar[Literal["eval", "exec"]] = "exec"

    def execute(self, context: Context, **bindings: object) -> None:
        """Run the statements."""
        exec(self._code, self._namespace(context, **bindings))  # noqa: S102


class NumPyExpressionCfg(ExpressionCfg):
    """Configuration for a NumPy expression."""

    model_config = ConfigDict(coerce_numbers_to_str=True)

    @overload
    def contextualize(self, context: Context, typeguard: NamedTypeguard[T]) -> T: ...
    @overload
    def contextualize(self, context: Context, typeguard: None = None) -> object: ...
    def contextualize(
        self, context: Context, typeguard: NamedTypeguard[T] | None = None
    ) -> object:
        """Evaluate the expression with an optional typeguard check."""
        if typeguard is None:
            return self.evaluate(context)
        return self.evaluate_typed(context, typeguard)


class NonNegativeTimeFnCfg(ExpressionCfg):
    """Configuration for a non-negative float expression of the time."""

    def contextualize(self, context: Context) -> Callable[[Any], float]:
        """Return a function of time ``t`` that runs the source."""

        def fn(t: Any) -> float:
            value = self.evaluate_typed(context, FLOAT_TG, t=t)
            if value < 0:
                raise ValueError(
                    f"Expression {self.root!r} evaluated to a negative value {value}."
                )
            return value

        return fn


class ModelExpressionCfg(ExpressionCfg):
    """Configuration for an expression of the current model with any result."""

    def contextualize(self, context: Context) -> Callable[[Any], object]:
        """Return a function of ``model`` that runs the source."""
        return lambda model: self.evaluate(context, model=model)


class NonNegativeModelFnCfg(ExpressionCfg):
    """Configuration for a non-negative float expression of the current model."""

    def contextualize(self, context: Context) -> Callable[[Any], float]:
        """Return a function of ``model`` that runs the source."""

        def fn(model: Any) -> float:
            value = self.evaluate_typed(context, FLOAT_TG, model=model)
            if value < 0:
                raise ValueError(
                    f"Expression {self.root!r} evaluated to a negative value {value}."
                )
            return value

        return fn


class ModelPredicateCfg(ExpressionCfg):
    """Configuration for a boolean expression of the current model."""

    def contextualize(self, context: Context) -> Callable[[Any], bool]:
        """Return a function of ``model`` that runs the source."""

        def predicate(model: Any) -> bool:
            return self.evaluate_typed(context, BOOL_TG, model=model)

        return predicate


class ModelActionCfg(StatementCfg):
    """Configuration for statements acting on the current model."""

    def contextualize(self, context: Context) -> Callable[[Any], None]:
        """Return a function of ``model`` that runs the source."""

        def action(model: Any) -> None:
            self.execute(context, model=model)

        return action


class OutputHookCfg(StatementCfg):
    """Configuration for statements of the current model and the sample's output directory."""

    def contextualize(self, context: Context) -> Callable[[Any, Any], None]:
        """Return a function of ``model`` and ``output_dir`` that runs the source."""

        def hook(model: Any, output_dir: Any) -> None:
            self.execute(context, model=model, output_dir=output_dir)

        return hook
