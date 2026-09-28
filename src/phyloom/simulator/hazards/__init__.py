"""Model time-varying event rates in simulations."""

from phyloom.simulator.hazards._constant import ConstantHazard
from phyloom.simulator.hazards._delta import DeltaHazard
from phyloom.simulator.hazards._exponential import ExponentialHazard
from phyloom.simulator.hazards._hazard import Hazard
from phyloom.simulator.hazards._numeric import NumericHazard
from phyloom.simulator.hazards._skyline import SkylineHazard

__all__ = [
    "ConstantHazard",
    "DeltaHazard",
    "ExponentialHazard",
    "Hazard",
    "NumericHazard",
    "SkylineHazard",
]
