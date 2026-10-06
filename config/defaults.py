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
        inbound_delay_enabled=True,
        inbound_delay_prob=0.4,
        inbound_delay_mean_steps=2.0,
        gdp_enabled=True,
        gdp_capacity_threshold=0.7,
        irops_enabled=True,
        irops_cancel_delay_threshold_steps=15,
        irops_max_cancels_per_step=2,
        n_remote_stands=10,
        remote_bus_transfer_steps=2,
        widebody_share=0.15,
        widebody_gate_share=0.25,
        gate_buffer_steps=1,
        connecting_passenger_share=0.35,
        mct_steps=6,
        terminal_los_enabled=True,
        terminal_capacity_enforced=False,
        los_overcrowd_mct_penalty_steps=2,
        baggage_enabled=True,
        bags_per_passenger=1.0,
        bag_unload_steps=2,
        bag_transfer_steps=3,
        bag_make_up_steps=2,
        bag_claim_steps=2,
        bag_hold_departure=True,
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
        from .copy_config import copy_simulation_config
        return copy_simulation_config(cfg, seed=seed)
    return cfg
