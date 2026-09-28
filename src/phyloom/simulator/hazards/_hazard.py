from abc import ABC, abstractmethod


class Hazard(ABC):
    r"""Base class for time-dependent event rates.

    A hazard is a non-negative instantaneous event rate :math:`\lambda(t)`,
    where :math:`t` is time. Starting at time :math:`t_0`, the cumulative
    hazard :math:`H(t_0, t)` at a later time :math:`t` is

    .. math::

       H(t_0, t) = \int_{t_0}^{t} \lambda(s)\,\mathrm{d}s.

    To schedule an event, the simulator draws a positive threshold :math:`c`,
    representing the random amount of event pressure that must accumulate before
    the event occurs. The inverse cumulative hazard gives the corresponding
    event time:

    .. math::

       H^{-1}(t_0, c) = \inf\{t \geq t_0 : H(t_0, t) \geq c\}.

    A larger hazard accumulates event pressure more quickly and therefore
    leads to shorter expected waiting times.

    The inversion mechanics are delegated to subclasses, which implement
    :meth:`invert` for their specific rate function.
    """

    @abstractmethod
    def invert(self, t0: float, threshold: float) -> float | None:
        r"""Find the time at which a cumulative-hazard threshold is met.

        Args:
            t0: Non-negative starting time :math:`t_0`.
            threshold: Positive cumulative-hazard threshold :math:`c`.

        Returns:
            The earliest time :math:`t \geq t_0` at which the threshold is met,
            or ``None`` if it is never met.
        """

    def _validate(self, t0: float, threshold: float) -> None:
        if threshold <= 0:
            raise ValueError(f"Threshold must be positive (got threshold={threshold}).")
        if t0 < 0:
            raise ValueError(f"Time must be non-negative (got t0={t0}).")
