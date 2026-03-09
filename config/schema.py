"""
Configuration schema: dataclasses for all model parameters.
Single source of truth for parameterization.
"""

from dataclasses import dataclass, field
from typing import Tuple, Optional


@dataclass(frozen=True)
class WeatherConfig:
    """Weather / shock parameters."""
    shock_at_step: Optional[int] = 60
    shock_duration: int = 12
    normal_variation_prob: float = 0.02


@dataclass(frozen=True)
class AirportConfig:
    """Airport capacity, runway, gates, and taxi parameters."""
    runway_slots_per_step: int = 4
    terminal_capacity: int = 2000
    n_gates: int = 20
    n_airlines: int = 3
    taxi_in_steps: int = 2
    taxi_out_steps: int = 2
    disembark_steps: int = 3
    board_steps: int = 3


@dataclass(frozen=True)
class ShockConfig:
    """Shock scenario (can override WeatherConfig for a run)."""
    enabled: bool = True
    at_step: Optional[int] = 60
    duration: int = 12


# Default gate and flight-share distribution (e.g. one dominant airline, two smaller)
DEFAULT_GATES_PER_AIRLINE = (70, 15, 15)  # 100 gates total, 3 airlines
DEFAULT_AIRLINE_FLIGHT_SHARE = (0.8, 0.1, 0.1)


@dataclass(frozen=True)
class ModelConfig:
    """Core model parameters."""
    n_steps: int = 200
    flights_per_step: float = 2.5
    passengers_per_flight: Tuple[int, int] = (80, 150)
    runway_slots_per_step: int = 5
    terminal_capacity: int = 5000
    n_gates: int = 100
    n_airlines: int = 3
    taxi_in_steps: int = 3
    taxi_out_steps: int = 3
    disembark_steps: int = 3
    board_steps: int = 3
    gates_per_airline: Optional[Tuple[int, ...]] = DEFAULT_GATES_PER_AIRLINE  # If None, equal split
    airline_flight_share: Optional[Tuple[float, ...]] = DEFAULT_AIRLINE_FLIGHT_SHARE  # If None, uniform
    seed: Optional[int] = None


@dataclass
class RunConfig:
    """CLI / single-run overrides."""
    steps: int = 150
    shock_at: Optional[int] = 60
    shock_duration: int = 12
    seed: int = 42
    no_shock: bool = False
    runs: int = 1
    output_path: Optional[str] = None
    metrics_path: Optional[str] = None


@dataclass
class SimulationConfig:
    """
    Full configuration for one simulation.
    Built from ModelConfig + ShockConfig (or RunConfig).
    """
    n_steps: int
    flights_per_step: float
    passengers_per_flight: Tuple[int, int]
    runway_slots_per_step: int
    terminal_capacity: int
    n_gates: int
    n_airlines: int
    taxi_in_steps: int
    taxi_out_steps: int
    disembark_steps: int
    board_steps: int
    gates_per_airline: Optional[Tuple[int, ...]] = None  # If None, equal split
    airline_flight_share: Optional[Tuple[float, ...]] = None  # If None, uniform
    seed: Optional[int] = None
    shock_at_step: Optional[int] = None
    shock_duration: int = 12

    @classmethod
    def from_model_and_shock(
        cls,
        model: ModelConfig,
        shock: ShockConfig,
    ) -> "SimulationConfig":
        return cls(
            n_steps=model.n_steps,
            flights_per_step=model.flights_per_step,
            passengers_per_flight=model.passengers_per_flight,
            runway_slots_per_step=model.runway_slots_per_step,
            terminal_capacity=model.terminal_capacity,
            n_gates=model.n_gates,
            n_airlines=model.n_airlines,
            taxi_in_steps=model.taxi_in_steps,
            taxi_out_steps=model.taxi_out_steps,
            disembark_steps=model.disembark_steps,
            board_steps=model.board_steps,
            gates_per_airline=model.gates_per_airline,
            airline_flight_share=model.airline_flight_share,
            seed=model.seed,
            shock_at_step=shock.at_step if shock.enabled else None,
            shock_duration=shock.duration,
        )
