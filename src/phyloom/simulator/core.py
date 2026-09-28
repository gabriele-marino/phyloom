"""Building blocks for event-driven stochastic simulation models."""

from __future__ import annotations

from random import Random
from typing import TYPE_CHECKING, Generic, Protocol, TypeVar

from phyloom.utils import PriorityBuckets

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from typing_extensions import Self

    from phyloom.simulator.hazards import Hazard


ModelT = TypeVar("ModelT", bound="Model")
ModelT_co = TypeVar("ModelT_co", bound="Model", covariant=True)
ModelT_contra = TypeVar("ModelT_contra", bound="Model", contravariant=True)


class EventRule(Protocol[ModelT_contra]):
    """Defines state transition eligibility and mutation logic for a stochastic event.

    An ``EventRule`` governs *how* state changes occur within a model, while its
    associated hazard governs *when* the event fires. A single rule manages one or
    more "opportunities"—individual elementary state transitions currently available
    in the model (e.g., an active lineage eligible for death, a source-recipient
    pair for infection, or a lineage pair for coalescence). The opportunity count
    directly scales the per-opportunity hazard to compute the total rate for the event.

    Implementations must calculate opportunities without modifying the target model
    and, upon execution, apply exactly one valid transition (typically by sampling
    an opportunity uniformly at random and mutating the model state in place).
    """

    def opportunities(self, model: ModelT_contra) -> int:
        """Calculate the number of elementary state transitions currently available.

        A return value of ``0`` indicates that the event is inactive in the current
        model state and cannot be selected by the simulator.
        """
        raise NotImplementedError

    def apply(self, model: ModelT_contra):
        """Select and execute a single eligible transition on the model.

        Mutates the target ``model`` state according to the event's rule semantics.
        The simulator guarantees this method is invoked only when :meth:`opportunities`
        returns a positive count for the current model state.
        """


class Event(Generic[ModelT_contra]):
    """Represents a discrete stochastic state transition with a sampled firing time.

    An ``Event`` binds an :class:`EventRule` (governing state mutations and
    opportunity counts) to a per-opportunity :class:`~phyloom.simulator.hazards.Hazard`
    (governing time-dependent rates).

    To propose a firing time, the event queries the rule's active opportunity count,
    samples an exponential waiting threshold, and converts that threshold into an
    absolute time via the hazard. An optional state-dependent rate multiplier further
    scales the overall event rate. Higher opportunity counts or larger multipliers
    increase the total hazard rate, resulting in shorter expected waiting times.

    Upon selection by the simulator, the event delegates the actual state mutation
    back to its underlying rule. This design decouples event scheduling from model
    mutation logic.

    Args:
        rule: Governs eligibility, opportunity counting, and state mutation.
        hazard: The time-dependent per-opportunity hazard used to sample firing times.
        rate_multiplier: An optional callable computing a non-negative rate-scaling
            factor from the model state. Returning zero disables the event.
    """

    def __init__(
        self,
        rule: EventRule[ModelT_contra],
        hazard: Hazard,
        *,
        rate_multiplier: Callable[[ModelT_contra], float] | None = None,
    ):
        self._hazard = hazard
        self._rule = rule
        self._rate_multiplier = rate_multiplier

    def query_firing_time(self, model: ModelT_contra) -> float | None:
        """Sample the next proposed firing time for this event given the current model state.

        Draws a standard exponential random variate, scales it by the active opportunity
        count and any configured rate multiplier, and passes the resulting integrated
        hazard threshold to the underlying hazard function to invert into an absolute time.

        Args:
            model: The target simulation model state to evaluate.

        Returns:
            The absolute proposed firing time, or ``None`` if the event is inactive
            (e.g., zero opportunities or zero rate multiplier).
        """
        opportunities = self._rule.opportunities(model)
        if not opportunities:
            return None
        threshold = model.rng.expovariate(1.0) / opportunities
        if self._rate_multiplier is not None:
            multiplier = self._rate_multiplier(model)
            if multiplier < 0:
                raise ValueError(
                    f"Rate multiplier must be finite and non-negative (got {multiplier})."
                )
            if not multiplier:
                return None
            threshold /= multiplier
        return self._hazard.invert(model.current_time, threshold)

    def apply(self, model: ModelT_contra):
        """Execute the state mutation associated with this event.

        Delegates to the underlying :class:`EventRule` to select and apply a single
        eligible transition to ``model``.
        """
        self._rule.apply(model)


class Model:
    """Base class for stepwise stochastic discrete-event simulations.

    A ``Model`` stores a simulated clock, stochastic events, and deterministic
    actions scheduled at absolute times. Call :meth:`step` repeatedly to advance
    the clock and apply transitions. On each call, the model samples proposed
    firing times for its events, advances to the earliest proposal, scheduled
    action, or supplied time limit, and applies all transitions due at that
    time. Transitions due simultaneously are applied in random order.

    Concrete subclasses represent the domain state being modeled, such as a
    population, phylogenetic tree, or epidemiological network. State-transition
    implementations can use :attr:`rng`, inspect :attr:`current_time`, and add
    further events or actions with :meth:`add_event` and :meth:`add_action`.
    The model does not reset its clock, events, scheduled actions, or subclass
    state; callers control the simulation lifecycle.

    Args:
        events: Stochastic events governing continuous-time state transitions.
        schedule: Iterable of ``(time, action)`` pairs. An action receives and
            mutates the model when its time is reached. Actions scheduled for
            the same time are shuffled before execution.
    """

    def __init__(
        self,
        events: Iterable[Event[Self]] = (),
        schedule: Iterable[tuple[float, Callable[[Self], None]]] = (),
    ):
        self._rng = Random()
        self._current_time: float = 0.0
        self._events = list(events)

        if any(t < 0 for t, _ in schedule):
            raise ValueError("Scheduled event times must be non-negative.")
        self._schedule = PriorityBuckets(schedule)

    @property
    def rng(self) -> Random:
        """Internal pseudo-random number generator.

        Use this generator for any stochasticity in state-transition
        implementations to ensure reproducibility.
        """
        return self._rng

    @property
    def current_time(self) -> float:
        """The current simulated clock time of the model."""
        return self._current_time

    def add_event(self, event: Event[Self]):
        """Dynamically add a new stochastic event to the model."""
        self._events.append(event)

    def add_action(self, time: float, rule: Callable[[Self], None]):
        """Dynamically schedule a deterministic action at the specified time."""
        if time < self._current_time:
            raise ValueError(
                f"Cannot schedule an event in the past (got time={time} "
                f"at current_time={self._current_time})."
            )
        self._schedule.push(time, rule)

    def step(self, max_time: float | None = None) -> bool:
        """Advance the simulation clock to the next transition time and apply all due transitions.

        The clock advances to the earliest proposed stochastic event, scheduled
        action, or ``max_time``. All events and actions due at that time are
        applied in random order. Supplying ``max_time`` prevents the clock from
        advancing beyond that time, but does not prevent events or actions
        scheduled for that time from being applied.

        Args:
            max_time: Optional inclusive upper limit for the simulated clock.

        Returns:
            ``False`` when no transition is applied, either because none is
            possible or because the next transition is after ``max_time``;
            ``True`` when a transition is applied, including at ``max_time``.
        """
        if max_time is not None and max_time < self._current_time:
            raise ValueError(
                f"Cannot step to a time in the past (got max_time={max_time} "
                f"at current_time={self._current_time})."
            )

        next_event_times = [e.query_firing_time(self) for e in self._events]
        next_step_times = [t for t in next_event_times if t is not None]
        if any(t < self._current_time for t in next_event_times if t is not None):
            raise RuntimeError("Event firing time is in the past.")

        if self._schedule:
            next_step_times.append(self._schedule.peek_key())
        if max_time is not None and all(t > max_time for t in next_step_times):
            self._current_time = max_time
            return False
        if not next_step_times:
            return False
        self._current_time = min(next_step_times)

        should_apply: list[Callable[[Self], None]] = [
            event.apply
            for event, event_time in zip(self._events, next_event_times)
            if event_time == self._current_time
        ]
        if self._schedule and self._schedule.peek_key() == self._current_time:
            should_apply.extend(self._schedule.pop())

        if len(should_apply) > 1:
            self.rng.shuffle(should_apply)
        for apply in should_apply:
            apply(self)

        return True
