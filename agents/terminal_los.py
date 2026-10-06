"""
Terminal Level of Service (LoS) from occupancy vs terminal capacity.

Simplified IATA-style LoS bands based on occupancy ratio
(passengers in terminal / terminal capacity).
"""

from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from model.abm import AirportABM


class LevelOfService(str, Enum):
    """IATA-style Level of Service bands (A best → F worst)."""

    A = "A"
    B = "B"
    C = "C"
    D = "D"
    E = "E"
    F = "F"


def los_from_occupancy_ratio(ratio: float) -> LevelOfService:
    """Map occupancy / capacity to Level of Service."""
    if ratio <= 0.40:
        return LevelOfService.A
    if ratio <= 0.60:
        return LevelOfService.B
    if ratio <= 0.80:
        return LevelOfService.C
    if ratio <= 1.00:
        return LevelOfService.D
    if ratio <= 1.20:
        return LevelOfService.E
    return LevelOfService.F


class TerminalLoS:
    """
    Tracks terminal occupancy and Level of Service each step.

    When overcrowded (occupancy > terminal capacity), connecting passengers
    incur an MCT penalty (congestion slows connections).
    """

    def __init__(self, model: "AirportABM"):
        self.model = model
        self.occupancy = 0
        self.occupancy_ratio = 0.0
        self.level_of_service = LevelOfService.A
        self.overcrowded = False

    def step(self) -> None:
        from agents.traveler import TravelerState

        self.occupancy = sum(
            1
            for t in self.model.travelers
            if t.state in (TravelerState.IN_TERMINAL, TravelerState.OUTBOUND)
        )
        cap = max(1, self.model._config.terminal_capacity)
        self.occupancy_ratio = self.occupancy / cap
        self.level_of_service = los_from_occupancy_ratio(self.occupancy_ratio)
        self.overcrowded = self.occupancy > self.model._config.terminal_capacity

    def effective_mct_steps(self) -> int:
        """Minimum Connection Time, plus congestion penalty when overcrowded."""
        mct = self.model._config.mct_steps
        if not self.model._config.terminal_los_enabled:
            return mct
        if self.overcrowded:
            return mct + self.model._config.los_overcrowd_mct_penalty_steps
        return mct

    @property
    def los_code(self) -> str:
        return self.level_of_service.value
