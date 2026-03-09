"""
Traveler agents: inbound, in terminal, outbound, exited.
"""

from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from model.abm import AirportABM
    from .flight import Flight


class TravelerState(Enum):
    INBOUND = "inbound"
    IN_TERMINAL = "in_terminal"
    OUTBOUND = "outbound"
    EXITED = "exited"


class Traveler:
    """Passenger linked to arrival/departure flights. Tracks wait and stranded time."""

    _next_id = 0

    def __init__(
        self,
        model: "AirportABM",
        arrival_flight: "Flight | None" = None,
        departure_flight: "Flight | None" = None,
    ):
        Traveler._next_id += 1
        self.unique_id = f"traveler_{Traveler._next_id}"
        self.model = model
        self.arrival_flight = arrival_flight
        self.departure_flight = departure_flight
        self.state = (
            TravelerState.INBOUND if arrival_flight else TravelerState.IN_TERMINAL
        )
        self.entered_terminal_at: int | None = None
        self.exited_at: int | None = None
        self.total_wait_steps = 0

    def step(self) -> None:
        if self.state == TravelerState.EXITED:
            return
        current = self.model.steps
        if self.state == TravelerState.INBOUND and self.arrival_flight:
            if self.arrival_flight.state.name == "COMPLETED":
                self.state = TravelerState.IN_TERMINAL
                self.entered_terminal_at = current
            elif self.arrival_flight.state.name == "CANCELLED":
                self.total_wait_steps += 1
            return
        if self.state == TravelerState.IN_TERMINAL:
            if (
                self.departure_flight
                and self.departure_flight.state.name == "COMPLETED"
            ):
                self.state = TravelerState.EXITED
                self.exited_at = current
                if self.entered_terminal_at is not None:
                    self.total_wait_steps += current - self.entered_terminal_at
            elif (
                self.departure_flight
                and self.departure_flight.state.name == "CANCELLED"
            ):
                self.total_wait_steps += 1
            return
        if self.state == TravelerState.OUTBOUND and self.departure_flight:
            if self.departure_flight.state.name == "COMPLETED":
                self.state = TravelerState.EXITED
                self.exited_at = current

    def terminal_time(self) -> int | None:
        """Steps spent in terminal (if exited)."""
        if (
            self.entered_terminal_at is not None
            and self.exited_at is not None
        ):
            return self.exited_at - self.entered_terminal_at
        return None
