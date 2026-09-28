from phyloom.simulator.hazards._hazard import Hazard


class ConstantHazard(Hazard):
    r"""Hazard with a constant event rate.

    Given a positive rate :math:`r`, the instantaneous event rate at time
    :math:`t` is

    .. math::

       \lambda(t) = r.

    For starting time :math:`t_0`, later time :math:`t`, and positive
    threshold :math:`c`, the cumulative hazard :math:`H(t_0, t)` and
    its inversion are

    .. math::

       H(t_0,t) = r(t-t_0),
       \qquad
       H^{-1}(t_0,c) = t_0 + \frac{c}{r}.

    Args:
        rate: The constant event rate :math:`r`, which must be positive.
    """

    def __init__(self, rate: float):
        if rate <= 0:
            raise ValueError(f"Rate must be positive (got rate={rate}).")
        self._rate = rate

    def invert(self, t0: float, threshold: float) -> float | None:
        """Return the time at which the constant cumulative hazard reaches ``threshold``."""
        self._validate(t0, threshold)
        return t0 + threshold / self._rate
