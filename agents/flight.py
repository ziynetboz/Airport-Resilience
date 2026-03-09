"""
Flight agents: arrivals (landings) and departures (takeoffs).
Includes taxi time and gate occupancy.
"""

from enum import Enum
import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from model.abm import AirportABM


class FlightType(Enum):
    ARRIVAL = "arrival"
    DEPARTURE = "departure"


class FlightState(Enum):
    SCHEDULED = "scheduled"
    IN_QUEUE = "in_queue"
    EXECUTING = "executing"
    LANDED = "landed"  # Just landed, taxiing in
    TAXIING_IN = "taxiing_in"
    AT_GATE = "at_gate"
    TAXIING_OUT = "taxiing_out"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Flight:
    """A single flight (arrival or departure). Tracks delay, cancellation, taxi, and gate."""

    _next_id = 0

    def __init__(
        self,
        model: "AirportABM",
        flight_type: FlightType,
        scheduled_step: int,
        passenger_count: int = 100,
        airline_id: int = 0,
    ):
        Flight._next_id += 1
        self.unique_id = f"flight_{Flight._next_id}"
        self.model = model
        self.flight_type = flight_type
        self.scheduled_step = scheduled_step
        self.passenger_count = passenger_count
        self.airline_id = airline_id
        self.state = FlightState.SCHEDULED
        self.queued_at_step: int | None = None
        self.completed_at_step: int | None = None
        self.cancelled_at_step: int | None = None
        self.delay_steps = 0
        # Taxi and gate
        self.assigned_gate = None
        self.taxi_in_remaining: int = 0
        self.taxi_out_remaining: int = 0
        self.gate_occupancy_remaining: int = 0

    @property
    def delay(self) -> int:
        if self.state == FlightState.COMPLETED and self.completed_at_step is not None:
            return max(0, self.completed_at_step - self.scheduled_step - 1)
        if self.state in (FlightState.IN_QUEUE, FlightState.EXECUTING):
            return max(
                0,
                self.model.steps - (self.queued_at_step or self.scheduled_step),
            )
        return self.delay_steps

    def step(self) -> None:
        if self.state in (FlightState.COMPLETED, FlightState.CANCELLED):
            return
        weather = self.model.weather
        cancel_states = (
            FlightState.IN_QUEUE, FlightState.EXECUTING,
            FlightState.LANDED, FlightState.TAXIING_IN, FlightState.AT_GATE,
            FlightState.TAXIING_OUT,
        )
        if self.state in cancel_states and random.random() < weather.cancel_probability():
            self.state = FlightState.CANCELLED
            self.cancelled_at_step = self.model.steps
            if self.assigned_gate is not None:
                self.model.airport.release_gate(self)
                self.assigned_gate = None
            return
        if self.state == FlightState.IN_QUEUE:
            self.delay_steps = self.model.steps - (
                self.queued_at_step or self.scheduled_step
            )
            return

        airport = self.model.airport

        # Departure: SCHEDULED -> request gate -> AT_GATE -> TAXIING_OUT -> IN_QUEUE
        if self.state == FlightState.SCHEDULED and self.flight_type == FlightType.DEPARTURE:
            gate = airport.request_gate(self.airline_id)
            if gate is not None:
                gate.occupied_by = self
                self.assigned_gate = gate
                self.gate_occupancy_remaining = airport.board_steps
                self.state = FlightState.AT_GATE
            return

        airport = self.model.airport
        # Arrival: LANDED -> TAXIING_IN -> AT_GATE -> COMPLETED
        if self.state == FlightState.LANDED:
            self.taxi_in_remaining = airport.taxi_in_steps
            self.state = FlightState.TAXIING_IN
            return
        if self.state == FlightState.TAXIING_IN:
            self.taxi_in_remaining -= 1
            if self.taxi_in_remaining <= 0:
                gate = airport.request_gate(self.airline_id)
                if gate is not None:
                    gate.occupied_by = self
                    self.assigned_gate = gate
                    self.gate_occupancy_remaining = airport.disembark_steps
                    self.state = FlightState.AT_GATE
            return
        if self.state == FlightState.AT_GATE and self.flight_type == FlightType.ARRIVAL:
            self.gate_occupancy_remaining -= 1
            if self.gate_occupancy_remaining <= 0:
                airport.release_gate(self)
                self.assigned_gate = None
                self.state = FlightState.COMPLETED
                self.completed_at_step = self.model.steps
            return
        if self.state == FlightState.AT_GATE and self.flight_type == FlightType.DEPARTURE:
            self.gate_occupancy_remaining -= 1
            if self.gate_occupancy_remaining <= 0:
                airport.release_gate(self)
                self.assigned_gate = None
                self.taxi_out_remaining = airport.taxi_out_steps
                self.state = FlightState.TAXIING_OUT
            return
        if self.state == FlightState.TAXIING_OUT:
            self.taxi_out_remaining -= 1
            if self.taxi_out_remaining <= 0:
                airport.request_takeoff(self)
            return
