"""
Airline Operations Control (AOC) under irregular operations (IROPS).

Airports and ATC constrain capacity (weather, GDP). Airlines decide to
delay, cancel, or continue. This module implements a simple delay-threshold
cancellation policy.
"""

from typing import TYPE_CHECKING

from agents.cancel_reason import CancelReason
from agents.flight import Flight, FlightState, FlightType

if TYPE_CHECKING:
    from model.abm import AirportABM


class AirlineOperationsControl:
    """
    Airline IROPS decisions: cancel when projected delay exceeds a threshold.

    Prefer cancelling departures still at gate or not yet off-block over
    flights already taxiing or in the runway queue.
    """

    def __init__(
        self,
        model: "AirportABM",
        enabled: bool = True,
        cancel_delay_threshold_steps: int = 15,
        max_cancels_per_step: int = 2,
    ):
        self.model = model
        self.enabled = enabled
        self.cancel_delay_threshold_steps = cancel_delay_threshold_steps
        self.max_cancels_per_step = max_cancels_per_step
        self.cancels_this_step = 0

    def step(self) -> None:
        self.cancels_this_step = 0
        if not self.enabled:
            return

        candidates = self._candidate_flights()
        # Highest projected delay first; prefer not-yet-airborne/taxi states
        candidates.sort(key=lambda f: (-self._priority(f), -self._projected_delay(f)))

        for flight in candidates:
            if self.cancels_this_step >= self.max_cancels_per_step:
                break
            if self._projected_delay(flight) < self.cancel_delay_threshold_steps:
                continue
            self._cancel_flight(flight)

    def _candidate_flights(self) -> list[Flight]:
        eligible_states = {
            FlightState.SCHEDULED,
            FlightState.IN_QUEUE,
            FlightState.AT_GATE,
        }
        return [
            f
            for f in self.model.flights
            if f.state in eligible_states
        ]

    def _priority(self, flight: Flight) -> int:
        """Higher = more preferred to cancel (protect airborne/taxi movements)."""
        if flight.flight_type == FlightType.DEPARTURE and flight.state == FlightState.SCHEDULED:
            return 3
        if flight.flight_type == FlightType.DEPARTURE and flight.state == FlightState.AT_GATE:
            return 2
        if flight.flight_type == FlightType.ARRIVAL and flight.state == FlightState.SCHEDULED:
            return 2
        if flight.state == FlightState.IN_QUEUE:
            return 1
        return 0

    def _projected_delay(self, flight: Flight) -> int:
        """Steps late vs STA/STD, or waiting past ETA for unreleased arrivals."""
        if flight.state == FlightState.SCHEDULED and flight.flight_type == FlightType.ARRIVAL:
            ready = flight.eta_step if flight.eta_step is not None else flight.scheduled_time_step
            return max(0, self.model.steps - ready)
        if flight.state == FlightState.SCHEDULED and flight.flight_type == FlightType.DEPARTURE:
            return max(0, self.model.steps - flight.scheduled_time_step)
        return flight.delay_steps_vs_schedule

    def _cancel_flight(self, flight: Flight) -> None:
        if flight.state in (FlightState.COMPLETED, FlightState.CANCELLED):
            return
        flight.state = FlightState.CANCELLED
        flight.cancelled_at_step = self.model.steps
        flight.cancel_reason = CancelReason.AIRLINE_IROPS
        if flight.assigned_gate is not None:
            self.model.airport.release_gate(flight)
            flight.assigned_gate = None
        self.cancels_this_step += 1
        self.model.airport.flights_cancelled_this_step += 1

        # If inbound cancelled before completion, outbound on same registration typically cannot operate
        if (
            flight.flight_type == FlightType.ARRIVAL
            and flight.aircraft is not None
            and flight.aircraft.outbound_flight is not None
            and flight.aircraft.outbound_flight.state
            not in (FlightState.COMPLETED, FlightState.CANCELLED, FlightState.IN_QUEUE, FlightState.TAXIING_OUT)
        ):
            outbound = flight.aircraft.outbound_flight
            if outbound.state != FlightState.CANCELLED:
                outbound.state = FlightState.CANCELLED
                outbound.cancelled_at_step = self.model.steps
                outbound.cancel_reason = CancelReason.AIRLINE_IROPS
                if outbound.assigned_gate is not None:
                    self.model.airport.release_gate(outbound)
                    outbound.assigned_gate = None
                self.cancels_this_step += 1
                self.model.airport.flights_cancelled_this_step += 1
