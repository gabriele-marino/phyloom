"""Configuration types for validated Python source expressions and statements."""

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
    :meth:`evaluate_typed`, which take precedence over context names. The
    source is not sandboxed, so configuration input must be trusted.

    To write an expression type, subclass this class and implement
    ``contextualize`` so that it returns a function that evaluates the
    expression each time it is called, then checks the result.

    Examples:
        A non-negative rate that depends on the model and a lineage state:

        .. code-block:: python

           class MyRateCfg(ExpressionCfg):
               def contextualize(self, context: Context) -> Callable[[Any, Any], float]:
                   def rate(model: Any, state: Any) -> float:
                       value = self.evaluate_typed(
                           context, FLOAT_TG, model=model, state=state
                       )
                       if value < 0:
                           raise ValueError(f"Negative rate {value}.")
                       return value

                   return rate
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
    over context names. The source is not sandboxed, so configuration input
    must be trusted.

    To write a statement type, subclass this class and implement
    ``contextualize`` so that it returns a function that runs the statements
    each time it is called.

    Examples:
        A generic hook to update the model state:

        .. code-block:: python

           class MyHookCfg(StatementCfg):
               def contextualize(self, context: Context) -> Callable[[Any], None]:
                   def hook(model: Any) -> None:
                       self.execute(context, model=model)

                   return hook
    """

    _MODE: ClassVar[Literal["eval", "exec"]] = "exec"

    def execute(self, context: Context, **bindings: object) -> None:
        """Run the statements."""
        exec(self._code, self._namespace(context, **bindings))  # noqa: S102


class NumPyExpressionCfg(ExpressionCfg):
    """Configuration for a numerical expression with no extra bindings.

    Examples:
        Configure a derived context variable.

        .. code-block:: yaml

           context:
              generation_time: 2.5
              death_rate: np.exp(-0.1 * generation_time)
    """

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
    """Configuration for a non-negative float expression of the time ``t``.

    Examples:
        Configure the rate function of a numeric hazard that decays over time.

        .. code-block:: yaml

           context:
              rate_fn_decay: 0.1
           rate_fn: np.exp(-rate_fn_decay * t)
    """

    def contextualize(self, context: Context) -> Callable[[Any], float]:
        """Return a function of ``t`` that runs the source."""

        def fn(t: Any) -> float:
            value = self.evaluate_typed(context, FLOAT_TG, t=t)
            if value < 0:
                raise ValueError(
                    f"Expression {self.root!r} evaluated to a negative value {value}."
                )
            return value

        return fn


class ModelExpressionCfg(ExpressionCfg):
    """Configuration for a generic expression of the current ``model``.

    Examples:
        Configure context-dependent logging of model-derived values.

        .. code-block:: yaml

           context:
              generation_time: 2.5
           logs:
              sampled: model.count_sampled_lineages()
              expected: np.exp(-model.count_current_lineages() * generation_time)
    """

    def contextualize(self, context: Context) -> Callable[[Any], object]:
        """Return a function of ``model`` that runs the source."""
        return lambda model: self.evaluate(context, model=model)


class ModelNonNegativeFloatCfg(ExpressionCfg):
    """Configuration for a non-negative float expression of the current ``model``.

    Examples:
        Configure an event's rate multiplier that decreases as lineages accumulate.

        .. code-block:: yaml

           context:
              baseline_rate: 1.0
           rate_multiplier: baseline_rate / (1 + model.count_current_lineages())
    """

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
    """Configuration for a boolean expression of the current ``model``.

    Examples:
        Configure a stopping criterion based on a context-dependent threshold.

        .. code-block:: yaml

           context:
              target_samples: 20
           stop_criterion: model.count_sampled_lineages() >= target_samples
    """

    def contextualize(self, context: Context) -> Callable[[Any], bool]:
        """Return a function of ``model`` that runs the source."""

        def predicate(model: Any) -> bool:
            return self.evaluate_typed(context, BOOL_TG, model=model)

        return predicate


class ModelActionCfg(StatementCfg):
    """Configuration for statements acting on the current ``model``.

    Examples:
        Configure a context-dependent stop hook to update the model state
        after an accepted simulation trial.

        .. code-block:: yaml

           context:
              rho_A: 0.5
              rho_B: 0.6
           stop_hook: |
              model.rho_sample(rho_A, "A", removal=False)
              model.rho_sample(rho_B, "B", removal=True)
    """

    def contextualize(self, context: Context) -> Callable[[Any], None]:
        """Return a function of ``model`` that runs the source."""

        def action(model: Any) -> None:
            self.execute(context, model=model)

        return action


class OutputHookCfg(StatementCfg):
    """Configuration for statements of the current ``model`` and the sample's ``output_dir``.

    Examples:
        Configure an output hook that writes a sampled history to
        a Newick file in the sample output directory.

        .. code-block:: yaml

           output_hooks:
              - model.history(model.get_sampled_lineages()).dump(output_dir / "sampled.nwk")
    """

    def contextualize(self, context: Context) -> Callable[[Any, Any], None]:
        """Return a function of ``model`` and ``output_dir`` that runs the source."""

        def hook(model: Any, output_dir: Any) -> None:
            self.execute(context, model=model, output_dir=output_dir)

        return hook
