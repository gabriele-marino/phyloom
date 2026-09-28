from __future__ import annotations

from typing import TYPE_CHECKING

from scipy.integrate import quad
from scipy.optimize import brentq

from phyloom.simulator.hazards._hazard import Hazard

if TYPE_CHECKING:
    from collections.abc import Callable


class NumericHazard(Hazard):
    r"""Hazard defined by an arbitrary non-negative rate function.

    This hazard models :math:`\lambda(t) = f(t)` for a generic user-supplied
    function :math:`f` that returns the non-negative event rate at time
    :math:`t`. The cumulative hazard is evaluated by numerical quadrature
    and inversion uses a bracketed root solver. The search begins at
    :math:`t_0 + \mathrm{initial\_dt}` and doubles the search interval
    at most ``max_bracketing_steps`` times. If it cannot find a bracket,
    inversion returns ``None``; the threshold may be unreachable or the
    configured search limit may be too small.

    Args:
        rate_fn: Function :math:`f` that returns the non-negative event rate
            :math:`f(t)` at time :math:`t`.
        max_bracketing_steps: Maximum number of times to expand the time
            interval when searching for a bracket for the root solver.
        initial_dt: Initial width of the time interval to search for a
            bracket for the root solver.
    """

    def __init__(
        self,
        rate_fn: Callable[[float], float],
        *,
        max_bracketing_steps: int = 16,
        initial_dt: float = 1.0,
    ):
        def _rate_fn(t: float) -> float:
            rate = rate_fn(t)
            if rate < 0:
                raise ValueError(
                    f"Rate function must return non-negative values (got {rate})."
                )
            return rate

        self._rate_fn = _rate_fn

        if max_bracketing_steps <= 0:
            raise ValueError(
                f"The maximum number of bracketing steps must be positive (got max_bracketing_steps={max_bracketing_steps})."
            )
        if initial_dt <= 0:
            raise ValueError(
                f"The initial bracket width must be positive (got initial_dt={initial_dt})."
            )
        self._max_bracketing_steps = max_bracketing_steps
        self._initial_dt = initial_dt

    def invert(self, t0: float, threshold: float) -> float | None:
        """Invert the cumulative hazard by numerical integration and root finding."""
        self._validate(t0, threshold)

        def objective(t: float) -> float:
            integral, _ = quad(self._rate_fn, t0, t)
            return integral - threshold

        dt = self._initial_dt
        for _ in range(1, self._max_bracketing_steps + 1):
            hi = t0 + dt
            if objective(hi) >= 0:
                break
            dt *= 2
        else:
            return None

        return brentq(objective, t0, hi)
