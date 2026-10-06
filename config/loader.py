"""
Load configuration from external files (e.g. JSON, YAML).
Keeps parameterization separate from code.
"""

import json
from pathlib import Path
from typing import Any, Optional

from .schedule_mode import ScheduleMode
from .schema import (
    SimulationConfig,
    ModelConfig,
    ShockConfig,
    RunConfig,
)


def load_json(path: str | Path) -> dict[str, Any]:
    """Load a JSON file into a dict."""
    with open(path, "r") as f:
        return json.load(f)


def simulation_config_from_dict(data: dict[str, Any]) -> SimulationConfig:
    """Build SimulationConfig from a dict (e.g. from JSON)."""
    from .schema import DEFAULT_GATES_PER_AIRLINE, DEFAULT_AIRLINE_FLIGHT_SHARE
    gates = data.get("gates_per_airline")
    shares = data.get("airline_flight_share")
    return SimulationConfig(
        n_steps=int(data.get("n_steps", 200)),
        flights_per_step=float(data.get("flights_per_step", 2.5)),
        passengers_per_flight=tuple(data.get("passengers_per_flight", [80, 150])),
        runway_slots_per_step=int(data.get("runway_slots_per_step", 5)),
        terminal_capacity=int(data.get("terminal_capacity", 5000)),
        n_gates=int(data.get("n_gates", 100)),
        n_airlines=int(data.get("n_airlines", 3)),
        taxi_in_steps=int(data.get("taxi_in_steps", 3)),
        taxi_out_steps=int(data.get("taxi_out_steps", 3)),
        disembark_steps=int(data.get("disembark_steps", 3)),
        board_steps=int(data.get("board_steps", 3)),
        gates_per_airline=tuple(gates) if gates else DEFAULT_GATES_PER_AIRLINE,
        airline_flight_share=tuple(shares) if shares else DEFAULT_AIRLINE_FLIGHT_SHARE,
        schedule_mode=ScheduleMode(data.get("schedule_mode", ScheduleMode.PUBLISHED.value)),
        min_ground_time_steps=int(data.get("min_ground_time_steps", 9)),
        otp_on_time_tolerance_steps=int(data.get("otp_on_time_tolerance_steps", 1)),
        inbound_delay_enabled=bool(data.get("inbound_delay_enabled", True)),
        inbound_delay_prob=float(data.get("inbound_delay_prob", 0.4)),
        inbound_delay_mean_steps=float(data.get("inbound_delay_mean_steps", 2.0)),
        gdp_enabled=bool(data.get("gdp_enabled", True)),
        gdp_capacity_threshold=float(data.get("gdp_capacity_threshold", 0.7)),
        irops_enabled=bool(data.get("irops_enabled", True)),
        irops_cancel_delay_threshold_steps=int(
            data.get("irops_cancel_delay_threshold_steps", 15)
        ),
        irops_max_cancels_per_step=int(data.get("irops_max_cancels_per_step", 2)),
        seed=data.get("seed"),
        shock_at_step=data.get("shock_at_step"),
        shock_duration=int(data.get("shock_duration", 12)),
    )


def load_simulation_config(path: str | Path) -> SimulationConfig:
    """Load SimulationConfig from a JSON file."""
    data = load_json(path)
    return simulation_config_from_dict(data)


def run_config_from_dict(data: dict[str, Any]) -> RunConfig:
    """Build RunConfig from a dict."""
    return RunConfig(
        steps=int(data.get("steps", 150)),
        shock_at=data.get("shock_at", 60),
        shock_duration=int(data.get("shock_duration", 12)),
        seed=int(data.get("seed", 42)),
        no_shock=bool(data.get("no_shock", False)),
        runs=int(data.get("runs", 1)),
        output_path=data.get("output_path"),
        metrics_path=data.get("metrics_path"),
    )


def load_run_config(path: str | Path) -> RunConfig:
    """Load RunConfig from a JSON file (CLI overrides)."""
    data = load_json(path)
    return run_config_from_dict(data)
