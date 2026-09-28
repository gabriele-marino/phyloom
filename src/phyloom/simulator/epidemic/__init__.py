"""Compartmental epidemic simulation framework."""

from phyloom.simulator.epidemic._events import Flow, Infection, Migration, Recovery
from phyloom.simulator.epidemic._model import EpidemicModel

__all__ = ["EpidemicModel", "Flow", "Infection", "Migration", "Recovery"]
