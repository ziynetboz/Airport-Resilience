"""
Flight scheduling: stochastic injection or activation of a published flight schedule.
"""

import random
from typing import TYPE_CHECKING

from config.schedule_mode import ScheduleMode
from model.inbound_delay import draw_inbound_delay_steps

if TYPE_CHECKING:
    from model.abm import AirportABM


class FlightScheduler:
    """Creates flights (stochastic) or activates scheduled legs (published)."""

    def __init__(
        self,
        model: "AirportABM",
        flights_per_step: float = 2.0,
        passengers_per_flight: tuple[int, int] = (80, 150),
        airline_flight_share: "tuple[float, ...] | None" = None,
        schedule_mode: ScheduleMode = ScheduleMode.PUBLISHED,
    ):
        self.model = model
        self.flights_per_step = flights_per_step
        self.passengers_per_flight = passengers_per_flight
        self.airline_flight_share = airline_flight_share
        self.schedule_mode = schedule_mode

    def schedule_for_step(self) -> None:
        if self.schedule_mode == ScheduleMode.PUBLISHED:
            self._activate_published_legs()
        else:
            self._inject_stochastic_flights()

    def _activate_published_legs(self) -> None:
        """
        Release inbound when ETA is reached (STA + inbound delay).
        Release outbound when STD and MGT allow.
        """
        step = self.model.steps
        for ac in self.model.aircraft_rotations:
            inbound = ac.inbound_flight
            if inbound is not None and not ac.inbound_released:
                ready = (
                    inbound.eta_step
                    if inbound.eta_step is not None
                    else inbound.scheduled_time_step
                )
                if step >= ready:
                    ac.inbound_released = True
                    self.model.airport.request_landing(inbound)

            outbound = ac.outbound_flight
            if (
                outbound is not None
                and ac.inbound_released
                and not ac.outbound_released
                and ac.outbound_may_start(step)
            ):
                ac.outbound_released = True

    def _inject_stochastic_flights(self) -> None:
        """Legacy Poisson-style demand (no published timetable)."""
        n_new = self._draw_flight_count()
        for _ in range(n_new):
            is_arrival = random.random() < 0.5
            pax = random.randint(
                self.passengers_per_flight[0],
                self.passengers_per_flight[1],
            )
            from agents.flight import Flight, FlightType

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
            step = self.model.steps
            f = Flight(
                self.model,
                FlightType.ARRIVAL if is_arrival else FlightType.DEPARTURE,
                step,
                passenger_count=pax,
                airline_id=airline_id,
            )
            f.scheduled_time_step = step
            if is_arrival:
                delay = draw_inbound_delay_steps(self.model._config)
                f.inbound_delay_steps = delay
                f.eta_step = step + delay
                # Stochastic arrivals enter the landing stream at ETA via a hold flag
                if delay <= 0:
                    self.model.airport.request_landing(f)
                else:
                    self.model._stochastic_inbound_holds.append(f)
            self.model.flights.append(f)
            self._create_travelers_for_flight(f, is_arrival, pax)

        # Release stochastic arrivals whose ETA has arrived
        remaining = []
        for f in getattr(self.model, "_stochastic_inbound_holds", []):
            if f.state.name == "CANCELLED":
                continue
            ready = f.eta_step if f.eta_step is not None else f.scheduled_time_step
            if self.model.steps >= ready:
                self.model.airport.request_landing(f)
            else:
                remaining.append(f)
        self.model._stochastic_inbound_holds = remaining

    def _draw_flight_count(self) -> int:
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
