"""
Copy SimulationConfig with optional field overrides.

Avoids repeating every Phase A/B field when run.py / run_batch rebuild configs.
"""

from typing import Any, Optional

from .schema import SimulationConfig


def copy_simulation_config(
    cfg: SimulationConfig,
    **overrides: Any,
) -> SimulationConfig:
    """Return a new SimulationConfig, applying keyword overrides."""
    data = {
        "n_steps": cfg.n_steps,
        "flights_per_step": cfg.flights_per_step,
        "passengers_per_flight": cfg.passengers_per_flight,
        "runway_slots_per_step": cfg.runway_slots_per_step,
        "terminal_capacity": cfg.terminal_capacity,
        "n_gates": cfg.n_gates,
        "n_airlines": cfg.n_airlines,
        "taxi_in_steps": cfg.taxi_in_steps,
        "taxi_out_steps": cfg.taxi_out_steps,
        "disembark_steps": cfg.disembark_steps,
        "board_steps": cfg.board_steps,
        "gates_per_airline": cfg.gates_per_airline,
        "airline_flight_share": cfg.airline_flight_share,
        "schedule_mode": cfg.schedule_mode,
        "min_ground_time_steps": cfg.min_ground_time_steps,
        "otp_on_time_tolerance_steps": cfg.otp_on_time_tolerance_steps,
        "inbound_delay_enabled": cfg.inbound_delay_enabled,
        "inbound_delay_prob": cfg.inbound_delay_prob,
        "inbound_delay_mean_steps": cfg.inbound_delay_mean_steps,
        "gdp_enabled": cfg.gdp_enabled,
        "gdp_capacity_threshold": cfg.gdp_capacity_threshold,
        "irops_enabled": cfg.irops_enabled,
        "irops_cancel_delay_threshold_steps": cfg.irops_cancel_delay_threshold_steps,
        "irops_max_cancels_per_step": cfg.irops_max_cancels_per_step,
        "n_remote_stands": cfg.n_remote_stands,
        "remote_bus_transfer_steps": cfg.remote_bus_transfer_steps,
        "widebody_share": cfg.widebody_share,
        "widebody_gate_share": cfg.widebody_gate_share,
        "gate_buffer_steps": cfg.gate_buffer_steps,
        "connecting_passenger_share": cfg.connecting_passenger_share,
        "mct_steps": cfg.mct_steps,
        "terminal_los_enabled": cfg.terminal_los_enabled,
        "terminal_capacity_enforced": cfg.terminal_capacity_enforced,
        "los_overcrowd_mct_penalty_steps": cfg.los_overcrowd_mct_penalty_steps,
        "baggage_enabled": cfg.baggage_enabled,
        "bags_per_passenger": cfg.bags_per_passenger,
        "bag_unload_steps": cfg.bag_unload_steps,
        "bag_transfer_steps": cfg.bag_transfer_steps,
        "bag_make_up_steps": cfg.bag_make_up_steps,
        "bag_claim_steps": cfg.bag_claim_steps,
        "bag_hold_departure": cfg.bag_hold_departure,
        "seed": cfg.seed,
        "shock_at_step": cfg.shock_at_step,
        "shock_duration": cfg.shock_duration,
    }
    data.update(overrides)
    return SimulationConfig(**data)
