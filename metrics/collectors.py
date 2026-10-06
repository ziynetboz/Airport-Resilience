"""
Data collection: model reporters for time series and resilience analysis.
"""

from mesa.datacollection import DataCollector

from agents import TravelerState
from metrics.otp import compute_otp_metrics


def create_data_collector() -> DataCollector:
    """Build the DataCollector with all model-level reporters."""
    return DataCollector(
        model_reporters={
            "step": lambda m: m.steps,
            "flights_completed": lambda m: m.airport.flights_completed_this_step,
            "flights_cancelled": lambda m: m.airport.flights_cancelled_this_step,
            "arrival_queue": lambda m: m.airport.arrival_queue_length(),
            "departure_queue": lambda m: m.airport.departure_queue_length(),
            "weather_shock": lambda m: 1 if m.weather.is_shock() else 0,
            "weather_capacity_factor": lambda m: m.weather.capacity_factor(),
            "travelers_in_terminal": _travelers_in_terminal,
            "travelers_stranded": _travelers_stranded,
            "gates_available": lambda m: m.airport.gates_available(),
            "gate_utilization": lambda m: (
                1 - m.airport.gates_available() / m._config.n_gates
                if m._config.n_gates > 0 else 0.0
            ),
            "total_queue": lambda m: m.airport.total_queue_length(),
            "effective_slots": _effective_slots,
            "travelers_exited_this_step": _travelers_exited_this_step,
            "otp_arrival_pct": _otp_arrival_pct,
            "otp_departure_pct": _otp_departure_pct,
        }
    )


def _travelers_in_terminal(model) -> int:
    return sum(
        1 for t in model.travelers if t.state == TravelerState.IN_TERMINAL
    )


def _travelers_stranded(model) -> int:
    return sum(
        1
        for t in model.travelers
        if t.state == TravelerState.IN_TERMINAL
        and t.departure_flight
        and t.departure_flight.state.name == "CANCELLED"
    )


def _travelers_exited_this_step(model) -> int:
    """Travelers who transitioned to EXITED this step (cf2: operational continuity)."""
    return sum(
        1
        for t in model.travelers
        if t.state == TravelerState.EXITED
        and t.exited_at is not None
        and t.exited_at == model.steps
    )


def _otp_snapshot(model) -> dict:
    return compute_otp_metrics(
        model.flights,
        model._config.otp_on_time_tolerance_steps,
    )


def _otp_arrival_pct(model) -> float:
    snap = _otp_snapshot(model)
    return snap["otp_arrival_pct"] if snap["otp_arrival_pct"] is not None else float("nan")


def _otp_departure_pct(model) -> float:
    snap = _otp_snapshot(model)
    return snap["otp_departure_pct"] if snap["otp_departure_pct"] is not None else float("nan")


def _effective_slots(model) -> int:
    """Weather-reduced runway slots (for throughput efficiency, cf1)."""
    return max(
        1,
        int(model._config.runway_slots_per_step * model.weather.capacity_factor()),
    )
