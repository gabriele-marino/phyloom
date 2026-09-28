from math import exp, log, log1p

from phyloom.simulator.hazards._hazard import Hazard


class ExponentialHazard(Hazard):
    r"""Hazard whose rate changes exponentially with time.

    Given a positive base rate :math:`r` and decay parameter :math:`d`, this
    models

    .. math::

       \lambda(t) = r\,e^{-dt}.

    Its cumulative hazard is

    .. math::

       H(t_0,t) =
       \begin{cases}
       r(t-t_0), & d=0,\\[4pt]
       \dfrac{r}{d}\left(e^{-dt_0}-e^{-dt}\right), & d\ne 0.
       \end{cases}

    Therefore, for :math:`d\ne 0` and positive threshold :math:`c`, inversion is

    .. math::

       H^{-1}(t_0,c) = -\frac{1}{d}\log\left(e^{-dt_0}-\frac{dc}{r}\right)

    When :math:`d>0`, the total future cumulative hazard is

    .. math::

       \lim_{t\to\infty} H(t_0,t) = \frac{r}{d}e^{-dt_0};

    thresholds at or above this limit are never reached and inversion returns
    ``None``. Negative decay values model exponential growth and have no finite
    upper limit on cumulative hazard.

    Args:
        rate: The base rate :math:`r`, which must be positive.
        decay: The exponential decay parameter :math:`d`.
    """

    def __init__(self, rate: float, decay: float):
        if rate <= 0:
            raise ValueError(f"Rate must be positive (got rate={rate}).")

        self._rate = rate
        self._decay = decay

    def invert(self, t0: float, threshold: float) -> float | None:
        """Invert the exponential cumulative hazard analytically."""
        self._validate(t0, threshold)
        if not self._decay:
            return t0 + threshold / self._rate

        log_x = log(abs(self._decay) * threshold / self._rate) + self._decay * t0

        if self._decay < 0:
            growth = -self._decay
            if log_x > 0:
                return t0 + (log_x + log1p(exp(-log_x))) / growth
            return t0 + log1p(exp(log_x)) / growth

        if log_x >= 0:
            return None
        return t0 - log1p(-exp(log_x)) / self._decay
