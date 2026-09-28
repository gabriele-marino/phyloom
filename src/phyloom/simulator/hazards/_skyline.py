from __future__ import annotations

from bisect import bisect_right
from itertools import pairwise
from typing import TYPE_CHECKING

from phyloom.simulator.hazards._hazard import Hazard

if TYPE_CHECKING:
    from collections.abc import Sequence


class SkylineHazard(Hazard):
    r"""Hazard with a piecewise-constant rate over time intervals.

    Let :math:`m` be the number of break times, and let
    :math:`b_1 < \dots < b_m` be those times. With :math:`b_0 = 0` and
    :math:`b_{m+1} = \infty`, the event rate :math:`r_i` applies for each time
    :math:`t` between consecutive break times:

    .. math::

       \lambda(t) = r_i \quad\text{for}\quad b_i \leq t < b_{i+1}.

    For starting time :math:`t_0` and later time :math:`t`, the cumulative
    hazard :math:`H(t_0, t)` is the sum of the contributions from each
    interval:

    .. math::

       H(t_0,t) =
       \sum_{i=0}^{m} r_i
       \left[\min(t,b_{i+1})-\max(t_0,b_i)\right]_+,
       \qquad [x]_+ = \max(x,0).

    If the total cumulative hazard after :math:`t_0` is less than the threshold :math:`c`,
    inversion returns ``None``.

    Args:
        rates: Non-negative rates :math:`r_0,\dots,r_m`, one for each interval.
        break_times: Positive, strictly increasing interval boundaries
            :math:`b_1,\dots,b_m`.
    """

    def __init__(self, rates: Sequence[float], break_times: Sequence[float]):
        if len(rates) != len(break_times) + 1:
            raise ValueError(
                f"Number of rates must be one more than number of break times "
                f"(got {len(rates)} rates and {len(break_times)} break times)."
            )
        if any(t1 >= t2 for t1, t2 in pairwise(break_times)):
            raise ValueError(
                f"Break times must be sorted in strictly increasing order "
                f"(got break_times={break_times})."
            )
        if any(t <= 0 for t in break_times):
            raise ValueError(
                f"Break times must be positive (got break_times={break_times})."
            )
        if any(rate < 0 for rate in rates):
            raise ValueError(f"Rates must be non-negative (got rates={rates}).")

        self._rates = rates
        self._break_times = break_times

    def invert(self, t0: float, threshold: float) -> float | None:
        """Invert the piecewise-linear cumulative hazard interval by interval."""
        self._validate(t0, threshold)
        t = t0
        i = bisect_right(self._break_times, t0)
        remaining_threshold = threshold

        while True:
            rate = self._rates[i]
            next_change_time = (
                self._break_times[i] if i < len(self._break_times) else float("inf")
            )

            if rate:
                available = rate * (next_change_time - t)
                if remaining_threshold <= available:
                    return t + remaining_threshold / rate
                remaining_threshold -= available

            if next_change_time == float("inf"):
                return None

            t = next_change_time
            i += 1
