from phyloom.simulator.hazards._hazard import Hazard


class DeltaHazard(Hazard):
    r"""Degenerate hazard for an event occurring immediately.

    This hazard represents a point-mass event at the current time rather than
    an ordinary, absolutely continuous rate. For starting time :math:`t_0`
    and every positive threshold :math:`c`, inversion is defined as

    .. math::

       H^{-1}(t_0,c) = t_0.

    Thus, the event occurs at :math:`t_0` regardless of :math:`c`. This is
    useful for events that should fire as soon as they are eligible.
    """

    def invert(self, t0: float, threshold: float) -> float:
        """Return ``t0``, since the hazard fires immediately."""
        self._validate(t0, threshold)
        return t0
