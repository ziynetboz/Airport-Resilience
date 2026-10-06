"""
Main agent-based model: orchestrates agents, scheduler, and data collection.
"""

from mesa import Model

from config.schema import SimulationConfig
from config.schedule_mode import ScheduleMode
from agents import WeatherAgent, Airport
from agents.ground_delay_program import GroundDelayProgram
from agents.airline_ops import AirlineOperationsControl
from agents.gate_allocator import GateAllocator
from agents.terminal_los import TerminalLoS
from agents.baggage_handling import BaggageHandling, create_baggage_from_travelers
from metrics.collectors import create_data_collector
from .flight_scheduler import FlightScheduler
from .published_schedule import build_published_rotations
from .step_runner import StepRunner


class AirportABM(Model):
    """
    Airport under weather shocks (natural systems).
    Tracks landings/takeoffs, travelers, and resilience metrics.
    """

    def __init__(self, config: SimulationConfig):
        super().__init__(seed=config.seed)
        self._config = config

        self.weather = WeatherAgent(
            self,
            shock_at_step=config.shock_at_step,
            shock_duration=config.shock_duration,
        )

        self.airport = Airport(
            self,
            runway_slots_per_step=config.runway_slots_per_step,
            terminal_capacity=config.terminal_capacity,
            n_gates=config.n_gates,
            n_airlines=config.n_airlines,
            taxi_in_steps=config.taxi_in_steps,
            taxi_out_steps=config.taxi_out_steps,
            disembark_steps=config.disembark_steps,
            board_steps=config.board_steps,
            gates_per_airline=config.gates_per_airline,
            n_remote_stands=config.n_remote_stands,
            widebody_gate_share=config.widebody_gate_share,
            gate_buffer_steps=config.gate_buffer_steps,
        )

        self.flights: list = []
        self.travelers: list = []
        self.bags: list = []
        self.aircraft_rotations: list = []
        self._stochastic_inbound_holds: list = []

        self.gate_allocator = GateAllocator(self)
        self.terminal_los = TerminalLoS(self)
        self.baggage_handling = BaggageHandling(self)
        self.ground_delay_program = GroundDelayProgram(
            self,
            enabled=config.gdp_enabled,
            capacity_threshold=config.gdp_capacity_threshold,
        )
        self.airline_ops = AirlineOperationsControl(
            self,
            enabled=config.irops_enabled,
            cancel_delay_threshold_steps=config.irops_cancel_delay_threshold_steps,
            max_cancels_per_step=config.irops_max_cancels_per_step,
        )

        if config.schedule_mode == ScheduleMode.PUBLISHED:
            self.aircraft_rotations = build_published_rotations(self, config)
            create_baggage_from_travelers(self, config)

        self.flight_scheduler = FlightScheduler(
            self,
            flights_per_step=config.flights_per_step,
            passengers_per_flight=config.passengers_per_flight,
            airline_flight_share=config.airline_flight_share,
            schedule_mode=config.schedule_mode,
        )
        self.step_runner = StepRunner(self)
        self.datacollector = create_data_collector()

    @property
    def current_step(self) -> int:
        return self.steps

    @property
    def n_steps(self) -> int:
        return self._config.n_steps

    def step(self) -> None:
        self.step_runner.run_step()

    def run_model(self) -> None:
        for _ in range(self._config.n_steps - 1):
            self.step()
        self.step()

    def get_time_series(self):
        """Return collected data as a pandas DataFrame."""
        return self.datacollector.get_model_vars_dataframe()
