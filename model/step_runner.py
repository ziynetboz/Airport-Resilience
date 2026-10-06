"""
Step execution: defines the order of operations each time step.
Keeps the main model thin and testable.
"""

from typing import TYPE_CHECKING

from agents.flight import FlightState

if TYPE_CHECKING:
    from model.abm import AirportABM


class StepRunner:
    """
    One simulation step:

    1. Activate schedule / inject demand (STA/ETA/STD)
    2. Weather (capacity)
    3. Ground Delay Program (GDP / EDCT)
    4. Airline Operations Control (IROPS cancellations)
    5. Baggage handling (unload / transfer / make-up / claim)
    6. Flight airside progress
    7. Airport runway slots
    8. Travelers (connections / MCT)
    9. Terminal Level of Service (LoS)
    10. Data collection
    """

    def __init__(self, model: "AirportABM"):
        self.model = model

    def run_step(self) -> None:
        self.model.airport.flights_cancelled_this_step = 0
        self.model.gate_allocator.step()
        self.model.flight_scheduler.schedule_for_step()
        self.model.weather.step()
        self.model.ground_delay_program.step()
        self.model.airline_ops.step()
        self.model.baggage_handling.step()
        self._step_flights()
        self.model.airport.step()
        self._step_travelers()
        self.model.terminal_los.step()
        self.model.datacollector.collect(self.model)

    def _step_flights(self) -> None:
        for f in self.model.flights:
            if f.state not in (FlightState.COMPLETED, FlightState.CANCELLED):
                f.step()

    def _step_travelers(self) -> None:
        for t in self.model.travelers:
            t.step()
