"""
Default configuration instances.
Use these or override via config files / CLI.
"""

from typing import Optional
from .schedule_mode import ScheduleMode
from .schema import (
    ModelConfig,
    WeatherConfig,
    AirportConfig,
    ShockConfig,
    RunConfig,
    SimulationConfig,
)


def get_default_config() -> ModelConfig:
    """Default model parameters."""
    from .schema import DEFAULT_GATES_PER_AIRLINE, DEFAULT_AIRLINE_FLIGHT_SHARE
    return ModelConfig(
        n_steps=200,
        flights_per_step=2.5,
        passengers_per_flight=(80, 150),
        runway_slots_per_step=5,
        terminal_capacity=5000,
        n_gates=100,
        n_airlines=3,
        taxi_in_steps=3,
        taxi_out_steps=3,
        disembark_steps=3,
        board_steps=3,
        gates_per_airline=DEFAULT_GATES_PER_AIRLINE,
        airline_flight_share=DEFAULT_AIRLINE_FLIGHT_SHARE,
        schedule_mode=ScheduleMode.PUBLISHED,
        min_ground_time_steps=9,
        otp_on_time_tolerance_steps=1,
        seed=None,
    )


def get_weather_defaults() -> WeatherConfig:
    """Default weather / shock parameters."""
    return WeatherConfig(
        shock_at_step=60,
        shock_duration=12,
        normal_variation_prob=0.02,
    )


def get_airport_defaults() -> AirportConfig:
    """Default airport parameters."""
    return AirportConfig(
        runway_slots_per_step=5,
        terminal_capacity=5000,
        n_gates=100,
        n_airlines=3,
        taxi_in_steps=3,
        taxi_out_steps=3,
        disembark_steps=3,
        board_steps=3,
    )


def get_baseline_config(no_shock: bool = False) -> ShockConfig:
    """Baseline shock scenario (no shock for baseline runs)."""
    return ShockConfig(
        enabled=not no_shock,
        at_step=60,
        duration=12,
    )


def build_simulation_config(
    model: ModelConfig,
    shock_at_step: Optional[int] = None,
    shock_duration: int = 12,
    seed: Optional[int] = None,
) -> SimulationConfig:
    """Build SimulationConfig from model config and optional overrides."""
    from .schema import ShockConfig
    shock = ShockConfig(
        enabled=shock_at_step is not None,
        at_step=shock_at_step,
        duration=shock_duration,
    )
    cfg = SimulationConfig.from_model_and_shock(model, shock)
    if seed is not None:
        return SimulationConfig(
            n_steps=cfg.n_steps,
            flights_per_step=cfg.flights_per_step,
            passengers_per_flight=cfg.passengers_per_flight,
            runway_slots_per_step=cfg.runway_slots_per_step,
            terminal_capacity=cfg.terminal_capacity,
            n_gates=cfg.n_gates,
            n_airlines=cfg.n_airlines,
            taxi_in_steps=cfg.taxi_in_steps,
            taxi_out_steps=cfg.taxi_out_steps,
            disembark_steps=cfg.disembark_steps,
            board_steps=cfg.board_steps,
            gates_per_airline=cfg.gates_per_airline,
            airline_flight_share=cfg.airline_flight_share,
            schedule_mode=cfg.schedule_mode,
            min_ground_time_steps=cfg.min_ground_time_steps,
            otp_on_time_tolerance_steps=cfg.otp_on_time_tolerance_steps,
            seed=seed,
            shock_at_step=cfg.shock_at_step,
            shock_duration=cfg.shock_duration,
        )
    return cfg
