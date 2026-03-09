"""
Step execution: defines the order of operations each time step.
Keeps the main model thin and testable.
"""

from typing import TYPE_CHECKING

from agents.flight import FlightState

if TYPE_CHECKING:
    from model.abm import AirportABM


class StepRunner:
    """Runs one simulation step: schedule flights, weather, flights, airport, travelers, collect."""

    def __init__(self, model: "AirportABM"):
        self.model = model

    def run_step(self) -> None:
        """Execute one time step in the correct order."""
        self.model.flight_scheduler.schedule_for_step()
        self.model.weather.step()
        self._step_flights()
        self.model.airport.step()
        self._step_travelers()
        self.model.datacollector.collect(self.model)

    def _step_flights(self) -> None:
        for f in self.model.flights:
            if f.state not in (FlightState.COMPLETED, FlightState.CANCELLED):
                f.step()

    def _step_travelers(self) -> None:
        for t in self.model.travelers:
            t.step()
