"""
Flight scheduling: creates new flights and travelers for each step.
Single responsibility: turn model config and current step into new entities.
"""

import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from model.abm import AirportABM


class FlightScheduler:
    """Creates arrivals/departures and associated travelers each step."""

    def __init__(
        self,
        model: "AirportABM",
        flights_per_step: float = 2.0,
        passengers_per_flight: tuple[int, int] = (80, 150),
        airline_flight_share: "tuple[float, ...] | None" = None,
    ):
        self.model = model
        self.flights_per_step = flights_per_step
        self.passengers_per_flight = passengers_per_flight
        self.airline_flight_share = airline_flight_share

    def schedule_for_step(self) -> None:
        """Create new flights and travelers for the current step."""
        n_new = self._draw_flight_count()
        for _ in range(n_new):
            is_arrival = random.random() < 0.5
            pax = random.randint(
                self.passengers_per_flight[0],
                self.passengers_per_flight[1],
            )
            from agents.flight import Flight, FlightType
            from agents.traveler import Traveler, TravelerState

            n_airlines = len(self.model.airport.gate_pool._airline_gates)
            if (
                self.airline_flight_share is not None
                and len(self.airline_flight_share) == n_airlines
            ):
                airline_id = random.choices(
                    range(n_airlines),
                    weights=self.airline_flight_share,
                    k=1,
                )[0]
            else:
                airline_id = random.randint(0, n_airlines - 1) if n_airlines > 0 else 0
            f = Flight(
                self.model,
                FlightType.ARRIVAL if is_arrival else FlightType.DEPARTURE,
                self.model.steps,
                passenger_count=pax,
                airline_id=airline_id,
            )
            self.model.flights.append(f)
            if is_arrival:
                self.model.airport.request_landing(f)
            else:
                # Departures request gate first (via Flight.step), then taxi out, then takeoff
                pass
            self._create_travelers_for_flight(f, is_arrival, pax)

    def _draw_flight_count(self) -> int:
        """Number of new flights this step (stochastic from flights_per_step)."""
        n_new = random.choices(
            [int(self.flights_per_step), int(self.flights_per_step) + 1],
            weights=[
                1 - (self.flights_per_step % 1),
                self.flights_per_step % 1,
            ],
        )[0]
        return max(0, n_new)

    def _create_travelers_for_flight(
        self,
        flight,
        is_arrival: bool,
        passenger_count: int,
    ) -> None:
        from agents.traveler import Traveler, TravelerState

        step = self.model.steps
        if is_arrival:
            for _ in range(passenger_count):
                t = Traveler(self.model, arrival_flight=flight)
                self.model.travelers.append(t)
        else:
            for _ in range(passenger_count):
                t = Traveler(self.model, arrival_flight=None, departure_flight=flight)
                t.state = TravelerState.IN_TERMINAL
                t.entered_terminal_at = step - random.randint(1, 20)
                self.model.travelers.append(t)
