"""
Flight agents: arrivals (landings) and departures (takeoffs).
Includes taxi time and gate occupancy.
"""

from enum import Enum
from typing import TYPE_CHECKING

from agents.gate_class import AircraftType, GateUseType

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
        aircraft_type: AircraftType = AircraftType.NARROWBODY,
    ):
        Flight._next_id += 1
        self.unique_id = f"flight_{Flight._next_id}"
        self.model = model
        self.flight_type = flight_type
        self.scheduled_step = scheduled_step
        # STA for arrivals, STD for departures (published flight schedule)
        self.scheduled_time_step = scheduled_step
        self.passenger_count = passenger_count
        self.airline_id = airline_id
        self.aircraft_type = aircraft_type
        self.aircraft_registration: str | None = None
        self.aircraft = None  # Aircraft rotation, if any
        self.state = FlightState.SCHEDULED
        self.actual_arrival_step: int | None = None  # ATA (on-block at gate in this model)
        self.actual_departure_step: int | None = None  # ATD (takeoff from runway)
        # ETA (Estimated Time of Arrival): when the arrival may request landing
        self.eta_step: int | None = None
        self.inbound_delay_steps: int = 0
        # EDCT (Expect Departure Clearance Time) under Ground Delay Program (GDP)
        self.edct_step: int | None = None
        self.cancel_reason = None  # CancelReason when cancelled by airline IROPS
        self.queued_at_step: int | None = None
        self.completed_at_step: int | None = None
        self.cancelled_at_step: int | None = None
        self.delay_steps = 0
        # Taxi and gate
        self.assigned_gate = None
        self.gate_use_type: GateUseType | None = None
        self.taxi_in_remaining: int = 0
        self.taxi_out_remaining: int = 0
        self.gate_occupancy_remaining: int = 0

    @property
    def delay_steps_vs_schedule(self) -> int:
        """Elapsed steps late versus STA or STD."""
        sched = self.scheduled_time_step
        if self.flight_type == FlightType.ARRIVAL:
            if self.actual_arrival_step is not None:
                return max(0, self.actual_arrival_step - sched)
            if self.state in (
                FlightState.IN_QUEUE,
                FlightState.EXECUTING,
                FlightState.LANDED,
                FlightState.TAXIING_IN,
                FlightState.AT_GATE,
            ):
                return max(0, self.model.steps - sched)
        else:
            if self.actual_departure_step is not None:
                return max(0, self.actual_departure_step - sched)
            if self.state not in (
                FlightState.SCHEDULED,
                FlightState.COMPLETED,
                FlightState.CANCELLED,
            ):
                return max(0, self.model.steps - sched)
        return self.delay_steps

    @property
    def delay(self) -> int:
        return self.delay_steps_vs_schedule

    def _occupy_gate(self, gate, occupancy_steps: int) -> None:
        gate.occupied_by = self
        self.assigned_gate = gate
        self.gate_use_type = gate.use_type
        extra = 0
        if gate.use_type == GateUseType.REMOTE_STAND:
            extra = self.model._config.remote_bus_transfer_steps
        self.gate_occupancy_remaining = occupancy_steps + extra
        self.state = FlightState.AT_GATE

    def step(self) -> None:
        if self.state in (FlightState.COMPLETED, FlightState.CANCELLED):
            return
        # Cancellations are airline IROPS decisions (see AirlineOperationsControl),
        # not random weather draws on individual flights.
        if self.state == FlightState.IN_QUEUE:
            self.delay_steps = self.model.steps - (
                self.queued_at_step or self.scheduled_step
            )
            return

        airport = self.model.airport

        # Departure: SCHEDULED -> request gate -> AT_GATE -> TAXIING_OUT -> IN_QUEUE
        if self.state == FlightState.SCHEDULED and self.flight_type == FlightType.DEPARTURE:
            if self.aircraft is not None and not self.aircraft.outbound_released:
                return
            gate = airport.request_gate(self.airline_id, self.aircraft_type)
            if gate is not None:
                self._occupy_gate(gate, airport.board_steps)
            return

        # Arrival: LANDED -> TAXIING_IN -> AT_GATE -> COMPLETED
        if self.state == FlightState.LANDED:
            self.taxi_in_remaining = airport.taxi_in_steps
            self.state = FlightState.TAXIING_IN
            return
        if self.state == FlightState.TAXIING_IN:
            self.taxi_in_remaining -= 1
            if self.taxi_in_remaining <= 0:
                gate = airport.request_gate(self.airline_id, self.aircraft_type)
                if gate is not None:
                    self._occupy_gate(gate, airport.disembark_steps)
            return
        if self.state == FlightState.AT_GATE and self.flight_type == FlightType.ARRIVAL:
            self.gate_occupancy_remaining -= 1
            if self.gate_occupancy_remaining <= 0:
                airport.release_gate(self)
                self.assigned_gate = None
                self.state = FlightState.COMPLETED
                self.completed_at_step = self.model.steps
                self.actual_arrival_step = self.model.steps
                if self.aircraft is not None:
                    self.aircraft.record_inbound_on_block(
                        self.model.steps,
                        self.model._config.min_ground_time_steps,
                    )
            return
        if self.state == FlightState.AT_GATE and self.flight_type == FlightType.DEPARTURE:
            self.gate_occupancy_remaining -= 1
            if self.gate_occupancy_remaining <= 0:
                airport.release_gate(self)
                self.assigned_gate = None
                taxi = airport.taxi_out_steps
                if self.gate_use_type == GateUseType.REMOTE_STAND:
                    taxi += self.model._config.remote_bus_transfer_steps
                self.taxi_out_remaining = taxi
                self.state = FlightState.TAXIING_OUT
            return
        if self.state == FlightState.TAXIING_OUT:
            if self.taxi_out_remaining > 0:
                self.taxi_out_remaining -= 1
            if self.taxi_out_remaining <= 0:
                # GDP may assign EDCT before the flight joins the departure queue
                self.model.ground_delay_program.release_or_hold_for_takeoff(self)
            return
