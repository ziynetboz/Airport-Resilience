"""
Configuration schema: dataclasses for all model parameters.
Single source of truth for parameterization.
"""

from dataclasses import dataclass, field
from typing import Tuple, Optional

from .schedule_mode import ScheduleMode


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


# Preferential gates per airline; remainder of n_gates are common-use
# Default: 80 preferential + 20 common-use when n_gates=100
DEFAULT_GATES_PER_AIRLINE = (55, 12, 13)
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
    schedule_mode: ScheduleMode = ScheduleMode.PUBLISHED
    min_ground_time_steps: int = 9  # Minimum ground time (MGT) between on-block and off-block
    otp_on_time_tolerance_steps: int = 1  # OTP window in steps (discrete-time analog of OTP15)
    # Phase B: inbound delay, Ground Delay Program (GDP), airline IROPS
    inbound_delay_enabled: bool = True
    inbound_delay_prob: float = 0.4
    inbound_delay_mean_steps: float = 2.0
    gdp_enabled: bool = True
    gdp_capacity_threshold: float = 0.7
    irops_enabled: bool = True
    irops_cancel_delay_threshold_steps: int = 15
    irops_max_cancels_per_step: int = 2
    # Phase C: preferential / common-use / remote stands / gate class
    n_remote_stands: int = 10
    remote_bus_transfer_steps: int = 2
    widebody_share: float = 0.15
    widebody_gate_share: float = 0.25
    gate_buffer_steps: int = 1
    # Phase D: connecting passengers (MCT) and terminal Level of Service (LoS)
    connecting_passenger_share: float = 0.35
    mct_steps: int = 6
    terminal_los_enabled: bool = True
    terminal_capacity_enforced: bool = False  # soft: defer terminal entry when overcrowded
    los_overcrowd_mct_penalty_steps: int = 2
    # Phase E: baggage handling (transfer, make-up, claim)
    baggage_enabled: bool = True
    bags_per_passenger: float = 1.0
    bag_unload_steps: int = 2
    bag_transfer_steps: int = 3
    bag_make_up_steps: int = 2
    bag_claim_steps: int = 2
    bag_hold_departure: bool = True  # hold pushback until bags loaded or mishandled
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
    schedule_mode: ScheduleMode = ScheduleMode.PUBLISHED
    min_ground_time_steps: int = 9
    otp_on_time_tolerance_steps: int = 1
    inbound_delay_enabled: bool = True
    inbound_delay_prob: float = 0.4
    inbound_delay_mean_steps: float = 2.0
    gdp_enabled: bool = True
    gdp_capacity_threshold: float = 0.7
    irops_enabled: bool = True
    irops_cancel_delay_threshold_steps: int = 15
    irops_max_cancels_per_step: int = 2
    n_remote_stands: int = 10
    remote_bus_transfer_steps: int = 2
    widebody_share: float = 0.15
    widebody_gate_share: float = 0.25
    gate_buffer_steps: int = 1
    connecting_passenger_share: float = 0.35
    mct_steps: int = 6
    terminal_los_enabled: bool = True
    terminal_capacity_enforced: bool = False
    los_overcrowd_mct_penalty_steps: int = 2
    baggage_enabled: bool = True
    bags_per_passenger: float = 1.0
    bag_unload_steps: int = 2
    bag_transfer_steps: int = 3
    bag_make_up_steps: int = 2
    bag_claim_steps: int = 2
    bag_hold_departure: bool = True
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
            schedule_mode=model.schedule_mode,
            min_ground_time_steps=model.min_ground_time_steps,
            otp_on_time_tolerance_steps=model.otp_on_time_tolerance_steps,
            inbound_delay_enabled=model.inbound_delay_enabled,
            inbound_delay_prob=model.inbound_delay_prob,
            inbound_delay_mean_steps=model.inbound_delay_mean_steps,
            gdp_enabled=model.gdp_enabled,
            gdp_capacity_threshold=model.gdp_capacity_threshold,
            irops_enabled=model.irops_enabled,
            irops_cancel_delay_threshold_steps=model.irops_cancel_delay_threshold_steps,
            irops_max_cancels_per_step=model.irops_max_cancels_per_step,
            n_remote_stands=model.n_remote_stands,
            remote_bus_transfer_steps=model.remote_bus_transfer_steps,
            widebody_share=model.widebody_share,
            widebody_gate_share=model.widebody_gate_share,
            gate_buffer_steps=model.gate_buffer_steps,
            connecting_passenger_share=model.connecting_passenger_share,
            mct_steps=model.mct_steps,
            terminal_los_enabled=model.terminal_los_enabled,
            terminal_capacity_enforced=model.terminal_capacity_enforced,
            los_overcrowd_mct_penalty_steps=model.los_overcrowd_mct_penalty_steps,
            baggage_enabled=model.baggage_enabled,
            bags_per_passenger=model.bags_per_passenger,
            bag_unload_steps=model.bag_unload_steps,
            bag_transfer_steps=model.bag_transfer_steps,
            bag_make_up_steps=model.bag_make_up_steps,
            bag_claim_steps=model.bag_claim_steps,
            bag_hold_departure=model.bag_hold_departure,
            seed=model.seed,
            shock_at_step=shock.at_step if shock.enabled else None,
            shock_duration=shock.duration,
        )
