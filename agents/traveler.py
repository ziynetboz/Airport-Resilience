"""
Traveler agents: originating, terminating, and connecting passengers.
"""

from enum import Enum
from typing import TYPE_CHECKING, Optional

from agents.passenger_type import PassengerType

if TYPE_CHECKING:
    from model.abm import AirportABM
    from .flight import Flight


class TravelerState(Enum):
    INBOUND = "inbound"
    IN_TERMINAL = "in_terminal"
    OUTBOUND = "outbound"
    EXITED = "exited"
    MISCONNECTED = "misconnected"


class Traveler:
    """Passenger linked to arrival/departure flights. Tracks wait, stranding, misconnects."""

    _next_id = 0

    def __init__(
        self,
        model: "AirportABM",
        arrival_flight: "Flight | None" = None,
        departure_flight: "Flight | None" = None,
        passenger_type: PassengerType = PassengerType.ORIGINATING,
    ):
        Traveler._next_id += 1
        self.unique_id = f"traveler_{Traveler._next_id}"
        self.model = model
        self.arrival_flight = arrival_flight
        self.departure_flight = departure_flight
        self.passenger_type = passenger_type
        if passenger_type == PassengerType.ORIGINATING:
            self.state = TravelerState.IN_TERMINAL
        elif arrival_flight is not None:
            self.state = TravelerState.INBOUND
        else:
            self.state = TravelerState.IN_TERMINAL
        self.entered_terminal_at: int | None = None
        self.exited_at: int | None = None
        self.total_wait_steps = 0
        self.mct_steps: Optional[int] = None  # scheduled MCT at booking
        self.misconnected = False

    def step(self) -> None:
        if self.state in (TravelerState.EXITED, TravelerState.MISCONNECTED):
            return
        current = self.model.steps

        if self.state == TravelerState.INBOUND and self.arrival_flight:
            if self.arrival_flight.state.name == "COMPLETED":
                # Terminal entry may be deferred when over capacity (LoS enforcement)
                if self._may_enter_terminal():
                    self.state = TravelerState.IN_TERMINAL
                    self.entered_terminal_at = current
                else:
                    self.total_wait_steps += 1
            elif self.arrival_flight.state.name == "CANCELLED":
                self.total_wait_steps += 1
            return

        if self.state == TravelerState.IN_TERMINAL:
            if self.passenger_type == PassengerType.TERMINATING:
                # Local arrival: exit after one step in terminal
                self.state = TravelerState.EXITED
                self.exited_at = current
                if self.entered_terminal_at is not None:
                    self.total_wait_steps += current - self.entered_terminal_at
                return

            if self.passenger_type == PassengerType.CONNECTING:
                self._step_connecting(current)
                return

            # Originating
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
                if self.entered_terminal_at is not None:
                    self.total_wait_steps += current - self.entered_terminal_at
            elif self.departure_flight.state.name == "CANCELLED":
                self.total_wait_steps += 1
                self.state = TravelerState.IN_TERMINAL  # stranded connecting/originating
            return
    def _may_enter_terminal(self) -> bool:
        """Soft capacity: allow entry unless LoS enforcement and overcrowded."""
        cfg = self.model._config
        if not cfg.terminal_los_enabled or not cfg.terminal_capacity_enforced:
            return True
        return not self.model.terminal_los.overcrowded

    def _effective_mct(self) -> int:
        base = self.mct_steps if self.mct_steps is not None else self.model._config.mct_steps
        return self.model.terminal_los.effective_mct_steps() if hasattr(
            self.model, "terminal_los"
        ) else base

    def _step_connecting(self, current: int) -> None:
        dep = self.departure_flight
        if dep is None:
            return

        if dep.state.name == "CANCELLED":
            self.total_wait_steps += 1
            return

        # Departure already gone before passenger had MCT → misconnect
        if dep.state.name == "COMPLETED":
            mct = self._effective_mct()
            ready_at = (
                (self.entered_terminal_at + mct)
                if self.entered_terminal_at is not None
                else current + mct
            )
            # Available connection time from on-block to ATD
            atd = dep.actual_departure_step if dep.actual_departure_step is not None else current
            ata = self.entered_terminal_at if self.entered_terminal_at is not None else current
            available = atd - ata
            if available >= mct and ready_at <= atd:
                self.state = TravelerState.EXITED
                self.exited_at = current
                if self.entered_terminal_at is not None:
                    self.total_wait_steps += current - self.entered_terminal_at
            else:
                self._mark_misconnected(current)
            return

        # Still waiting for departure; if past ready time, treat as outbound in terminal
        mct = self._effective_mct()
        if (
            self.entered_terminal_at is not None
            and current >= self.entered_terminal_at + mct
        ):
            # Passenger has made MCT; remains until departure completes
            self.state = TravelerState.OUTBOUND
        return

    def _mark_misconnected(self, current: int) -> None:
        self.misconnected = True
        self.state = TravelerState.MISCONNECTED
        self.exited_at = current
        if self.entered_terminal_at is not None:
            self.total_wait_steps += current - self.entered_terminal_at

    def terminal_time(self) -> int | None:
        """Steps spent in terminal (if exited or misconnected)."""
        if (
            self.entered_terminal_at is not None
            and self.exited_at is not None
        ):
            return self.exited_at - self.entered_terminal_at
        return None
