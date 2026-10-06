"""
Airport: runway and terminal capacity, queues, slot allocation, gates, taxi.
"""

from collections import deque
import random
from typing import TYPE_CHECKING

from .flight import Flight, FlightState, FlightType
from .gate import Gate, GatePool

if TYPE_CHECKING:
    from model.abm import AirportABM


class Airport:
    """
    Runway and terminal. Allocates slots each step based on
    weather capacity factor; maintains arrival and departure queues.
    Manages gate pool and taxi times.
    """

    def __init__(
        self,
        model: "AirportABM",
        runway_slots_per_step: int = 4,
        terminal_capacity: int = 2000,
        n_gates: int = 20,
        n_airlines: int = 3,
        taxi_in_steps: int = 2,
        taxi_out_steps: int = 2,
        disembark_steps: int = 3,
        board_steps: int = 3,
        gates_per_airline: "tuple[int, ...] | None" = None,
    ):
        self.model = model
        self.runway_slots_per_step = runway_slots_per_step
        self.terminal_capacity = terminal_capacity
        self.taxi_in_steps = taxi_in_steps
        self.taxi_out_steps = taxi_out_steps
        self.disembark_steps = disembark_steps
        self.board_steps = board_steps
        self.gate_pool = GatePool(
            n_gates=n_gates,
            n_airlines=n_airlines,
            gates_per_airline=gates_per_airline,
        )
        self.arrival_queue: deque[Flight] = deque()
        self.departure_queue: deque[Flight] = deque()
        self.flights_completed_this_step = 0
        self.flights_cancelled_this_step = 0

    @property
    def weather(self):
        return self.model.weather

    def effective_slots(self) -> int:
        """Slots available this step (weather-reduced)."""
        return max(
            1,
            int(self.runway_slots_per_step * self.weather.capacity_factor()),
        )

    def request_landing(self, flight: Flight) -> None:
        if flight.state != FlightState.SCHEDULED:
            return
        flight.state = FlightState.IN_QUEUE
        flight.queued_at_step = self.model.steps
        self.arrival_queue.append(flight)

    def request_takeoff(self, flight: Flight) -> None:
        if flight.state not in (FlightState.SCHEDULED, FlightState.TAXIING_OUT):
            return
        flight.state = FlightState.IN_QUEUE
        flight.queued_at_step = self.model.steps
        self.departure_queue.append(flight)

    def request_gate(self, airline_id: int) -> "Gate | None":
        """Assign an available gate to the airline. Returns None if none free."""
        return self.gate_pool.request_gate(airline_id)

    def release_gate(self, flight: Flight) -> None:
        """Release the gate occupied by the flight."""
        self.gate_pool.release_gate(flight)

    def step(self) -> None:
        self.flights_completed_this_step = 0
        self.flights_cancelled_this_step = 0
        slots = self.effective_slots()
        for _ in range(slots):
            if not self.arrival_queue and not self.departure_queue:
                break
            use_arrival = (
                bool(self.arrival_queue)
                and (
                    not self.departure_queue
                    or len(self.arrival_queue) >= len(self.departure_queue)
                    or random.random() < 0.5
                )
            )
            if use_arrival and self.arrival_queue:
                f = self.arrival_queue.popleft()
                if f.state == FlightState.CANCELLED:
                    self.flights_cancelled_this_step += 1
                    continue
                f.state = FlightState.EXECUTING
                f.state = FlightState.LANDED  # Taxi in, gate, disembark before COMPLETED
                self.flights_completed_this_step += 1
            elif self.departure_queue:
                f = self.departure_queue.popleft()
                if f.state == FlightState.CANCELLED:
                    self.flights_cancelled_this_step += 1
                    continue
                f.state = FlightState.EXECUTING
                f.completed_at_step = self.model.steps
                f.actual_departure_step = self.model.steps
                f.state = FlightState.COMPLETED
                self.flights_completed_this_step += 1

    def arrival_queue_length(self) -> int:
        return len(self.arrival_queue)

    def departure_queue_length(self) -> int:
        return len(self.departure_queue)

    def total_queue_length(self) -> int:
        return len(self.arrival_queue) + len(self.departure_queue)

    def gates_available(self) -> int:
        return self.gate_pool.total_available()
