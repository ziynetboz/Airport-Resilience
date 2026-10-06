"""
Ground Delay Program (GDP): ATC Traffic Management Initiative (TMI).

When airport acceptance rate drops, ATC issues Expect Departure Clearance Times
(EDCT) so departures absorb delay on the ground rather than saturating the
arrival/departure stream. In this single-airport model, EDCT holds a departure
after taxi-out until the controlled time before it joins the departure queue.
"""

from typing import TYPE_CHECKING

from agents.flight import Flight, FlightState

if TYPE_CHECKING:
    from model.abm import AirportABM


class GroundDelayProgram:
    """
    Ground Delay Program (GDP).

    Active when the weather capacity factor is at or below
    ``gdp_capacity_threshold``. Assigns **EDCT** (Expect Departure Clearance
    Time) to departures finishing taxi-out.
    """

    def __init__(
        self,
        model: "AirportABM",
        enabled: bool = True,
        capacity_threshold: float = 0.7,
    ):
        self.model = model
        self.enabled = enabled
        self.capacity_threshold = capacity_threshold
        self.active = False
        self.edcts_assigned_this_step = 0
        self.flights_held_for_edct = 0

    def step(self) -> None:
        """Update GDP active flag from current capacity factor."""
        self.edcts_assigned_this_step = 0
        self.flights_held_for_edct = 0
        if not self.enabled:
            self.active = False
            return
        factor = self.model.weather.capacity_factor()
        self.active = factor <= self.capacity_threshold

    def is_active(self) -> bool:
        return self.active

    def release_or_hold_for_takeoff(self, flight: Flight) -> None:
        """
        After taxi-out: join the departure queue, or hold until EDCT under GDP.
        """
        if flight.state != FlightState.TAXIING_OUT:
            return
        if not self.active:
            self.model.airport.request_takeoff(flight)
            return

        if flight.edct_step is None:
            flight.edct_step = self._assign_edct()
            self.edcts_assigned_this_step += 1

        if self.model.steps >= flight.edct_step:
            self.model.airport.request_takeoff(flight)
        else:
            self.flights_held_for_edct += 1

    def _assign_edct(self) -> int:
        """
        Expect Departure Clearance Time (EDCT) as a future step index.

        Spacing grows when effective slots are scarce and the departure queue
        is long (simplified GDP rationing).
        """
        slots = max(1, self.model.airport.effective_slots())
        backlog = self.model.airport.departure_queue_length()
        # Hold steps proportional to backlog / acceptance rate
        hold = max(1, backlog // slots + 1)
        # Extra hold when capacity factor is low
        factor = max(0.05, self.model.weather.capacity_factor())
        hold = max(hold, int(round(1.0 / factor)))
        return self.model.steps + hold
