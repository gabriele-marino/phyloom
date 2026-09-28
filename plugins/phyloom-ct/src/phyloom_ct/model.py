"""Runtime contact-tracing model."""

# This is the runtime Python model, on top of which the configuration layer
# builds.

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from phyloom.simulator.bdsh import BDSHModel

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable
    from typing import TypeAlias

    from typing_extensions import Self

    from phyloom.simulator.core import Event
    from phyloom.types import NodeID

IndividualID: TypeAlias = int


# BDSHModel already provides the root lineage, active and sampled lineages by
# state, lineage times, and the network primitives. The subclass adds a layer
# of individuals on top, and three primitives (``transmission``, ``migration``,
# and ``recovery``), each built on a BDSH primitive (``birth_from``,
# ``continue_as``, ``finalize``, and ``sample``) plus the individual bookkeeping.
#
# A lineage is replaced on every change: a transmission ends the parent
# lineage and creates two new ones, and a state change creates a successor
# lineage. A lineage id therefore does not identify a person for long, so the
# model gives every individual a stable id, maps it to its current lineage,
# and maps every lineage, active or ended, to its individual.
class CTModel(BDSHModel):
    """Epidemic model with contact tracing of sampled individuals.

    The model evolves a transmission tree forward in time from one initial
    infected individual. Each active lineage represents one infected
    individual, and the model records who infected whom. Its primitives are:

    * :meth:`transmission` infects a new individual;
    * :meth:`migration` changes an individual's state; and
    * :meth:`recovery` removes an individual, optionally recording it as
      sampled. A sampled individual is an index case: each of its contacts
      (see :meth:`get_contacts`) that is still infected is independently
      notified with probability ``notification_probability``, and sampled and
      removed at the same time. Notified contacts are not traced further.

    The model builds these primitives on the BDSH ones. The BDSH primitives
    change the network but do not update the individuals, so they must not be
    called directly.

    Args:
        init_state: State of the initial infected individual.
        events: Stochastic events governing continuous-time state transitions.
        schedule: Iterable of ``(time, action)`` pairs. An action receives and
            mutates the model when its time is reached. Actions scheduled for
            the same time are shuffled before execution.
        notification_probability: Probability that each considered contact is
            notified after a sampled recovery. Must be between zero and one.
        max_notifications: Maximum number of contacts considered per sampled
            recovery. ``None`` considers all contacts; zero disables tracing.

    Examples:
        Simulate an SEI-like epidemic with tracing until at least 30
        individuals have been sampled.

        >>> from phyloom.simulator.core import Event
        >>> from phyloom.simulator.hazards import ConstantHazard
        >>> from phyloom_ct import CTModel, Migration, Recovery, Transmission
        >>> model = CTModel(
        ...     init_state="I",
        ...     events=[
        ...         Event(Transmission("I", child_state="E"), ConstantHazard(1.5)),
        ...         Event(Migration("E", "I"), ConstantHazard(2.0)),
        ...         Event(Recovery("I"), ConstantHazard(0.6)),
        ...         Event(Recovery("I", sample=True), ConstantHazard(0.4)),
        ...     ],
        ...     notification_probability=0.8,
        ...     max_notifications=5,
        ... )
        >>> model.rng.seed(0)
        >>> while model.step() and model.count_sampled_lineages() < 30:
        ...     pass
        >>> model.count_sampled_lineages()
        30

        Without stochastic events, and with ``notification_probability=1.0``,
        the model is deterministic, which is useful for testing: a
        ``schedule`` of actions that call the primitives builds a transmission
        chain step by step. Actions refer to individuals rather than lineages,
        because lineage ids change with every transmission and state change,
        and look up each individual's current lineage with :meth:`lineage_of`.

        >>> schedule = [
        ...     (1.0, lambda m: m.transmission(m.lineage_of(1), child_state="E")),
        ...     (2.0, lambda m: m.transmission(m.lineage_of(1), child_state="E")),
        ...     (3.0, lambda m: m.migration(m.lineage_of(2), "I")),
        ...     (4.0, lambda m: m.transmission(m.lineage_of(2), child_state="E")),
        ...     (5.0, lambda m: m.recovery(m.lineage_of(2), sample=True)),
        ... ]
        >>> model = CTModel(
        ...     init_state="I",
        ...     schedule=schedule,
        ...     notification_probability=1.0,
        ...     max_notifications=2,
        ... )
        >>> while model.step():
        ...     pass

        Sampling individual 2 at time 5 traces its infectee, 4, and its
        infector, 1. Individual 3 is not traced, because traced contacts do
        not start another round of tracing. Labeling each node with its
        individual makes this visible in the history.

        >>> for lineage, node in model.nodes.items():
        ...     node.set("individual", model.individual_of(lineage))
        >>> model.history().pretty_print()
        1|I (individual=1) [1.0]
        |-- 2|E (individual=2) [2.0]
        |   `-- 6|I (individual=2) [1.0]
        |       |-- 7|E (individual=4) [1.0]
        |       `-- 8|I (individual=2) [1.0]
        `-- 3|I (individual=1) [1.0]
            |-- 4|E (individual=3) [3.0]
            `-- 5|I (individual=1) [3.0]
        >>> model.get_contacts(2)
        [4, 1]
        >>> model.history(model.get_sampled_lineages()).pretty_print()
        1|I (individual=1) [1.0]
        |-- 5|I (individual=1) [4.0]
        `-- 6|I (individual=2) [3.0]
            |-- 8|I (individual=2) [1.0]
            `-- 7|E (individual=4) [1.0]
        >>> [model.individual_of(lin) for lin in model.get_current_lineages()]
        [3]
    """

    def __init__(
        self,
        init_state: str,
        events: Iterable[Event[Self]] = (),
        schedule: Iterable[tuple[float, Callable[[Self], None]]] = (),
        notification_probability: float = 1.0,
        max_notifications: int | None = None,
    ):
        if (
            not math.isfinite(notification_probability)
            or not 0.0 <= notification_probability <= 1.0
        ):
            raise ValueError(
                "notification_probability must be finite and between 0 and 1 "
                f"(got {notification_probability})."
            )
        if max_notifications is not None and (
            isinstance(max_notifications, bool) or max_notifications < 0
        ):
            raise ValueError(
                "max_notifications must be a non-negative integer or None "
                f"(got {max_notifications})."
            )
        super().__init__(init_state, events, schedule)
        self._notification_probability = notification_probability
        self._max_notifications = max_notifications

        # Individual bookkeeping: each individual maps to its current lineage,
        # and every lineage, active or ended, maps to its individual.
        # ``_contacts`` lists each individual's contacts in chronological
        # order: its infector first, then the individuals it infected.
        self._individual_to_lineage: dict[IndividualID, NodeID] = {}
        self._lineage_to_individual: dict[NodeID, IndividualID] = {}
        self._contacts: dict[IndividualID, list[IndividualID]] = {}
        self._next_individual_id: IndividualID = 0

        # The root lineage becomes individual 1, which has no infector.
        self._get_new_individual(self.get_root(), infector=None)

    def _get_new_individual(self, lineage: NodeID, infector: IndividualID | None):
        """Create a new individual for a lineage, optionally recording its infector."""
        self._next_individual_id += 1
        individual = self._next_individual_id
        self._contacts[individual] = [] if infector is None else [infector]
        if infector is not None:
            self._contacts[infector].append(individual)
        self._assign(individual, lineage)

    def _assign(self, individual: IndividualID, lineage: NodeID):
        """Assign an individual to a lineage, active or ended."""
        self._individual_to_lineage[individual] = lineage
        self._lineage_to_individual[lineage] = individual

    def individual_of(self, lineage: NodeID) -> IndividualID:
        """Return the individual represented by a lineage, active or ended."""
        if lineage not in self._lineage_to_individual:
            raise ValueError(f"Lineage {lineage} does not exist.")
        return self._lineage_to_individual[lineage]

    def lineage_of(self, individual: IndividualID) -> NodeID:
        """Return the current lineage of an individual, active or ended."""
        if individual not in self._individual_to_lineage:
            raise ValueError(f"Individual {individual} does not exist.")
        return self._individual_to_lineage[individual]

    def transmission(
        self,
        parent: NodeID,
        child_state: str | None = None,
        new_parent_state: str | None = None,
    ) -> tuple[NodeID, NodeID]:
        """Infect a new individual from an active parent lineage.

        Args:
            parent: Active lineage of the transmitting individual.
            child_state: State of the newly infected individual. If omitted, it
                inherits the parent's state.
            new_parent_state: State of the transmitting individual after the
                transmission. If omitted, it keeps its state.

        Returns:
            The continuing parent lineage and the new individual's lineage.
        """
        continuing, child = self.birth_from(parent, (new_parent_state, child_state))
        parent_id = self.individual_of(parent)
        self._assign(parent_id, continuing)
        self._get_new_individual(child, parent_id)
        return continuing, child

    def migration(self, lineage: NodeID, new_state: str) -> NodeID:
        """Change the state of an individual, keeping its identity.

        Args:
            lineage: Active lineage of the individual.
            new_state: New state of the individual.

        Returns:
            The individual's new lineage.
        """
        successor = self.continue_as(lineage, new_state)
        self._assign(self.individual_of(lineage), successor)
        return successor

    def get_contacts(self, individual: IndividualID) -> list[IndividualID]:
        """Return an individual's contacts, most recent first.

        The individuals it infected come first, most recent first, followed
        by its infector, if any. Tracing notifies contacts in this order.
        """
        return self._contacts[individual][::-1]

    def recovery(self, lineage: NodeID, *, sample: bool = False):
        """Remove an individual, optionally sampling it and tracing its contacts.

        Args:
            lineage: Active lineage of the individual.
            sample: Whether to record the individual as sampled. A sampled
                individual is an index case, whose contacts are traced.
        """
        # Tracing is not an event with its own rate but an immediate
        # consequence of sampling, so it happens here, inside the sampled
        # recovery.
        if not sample:
            self.finalize(lineage)
            return

        self.sample(lineage, removal=True)

        contacts = self.get_contacts(self.individual_of(lineage))
        if self._max_notifications is not None:
            contacts = contacts[: self._max_notifications]

        active_lineages = self._get_current_lineages()
        for contact in contacts:
            contact_lineage = self._individual_to_lineage[contact]
            if (
                contact_lineage in active_lineages
                and self.rng.random() < self._notification_probability
            ):
                # Sample directly rather than through ``recovery`` so that a
                # traced contact does not start another round of tracing.
                self.sample(contact_lineage, removal=True)
