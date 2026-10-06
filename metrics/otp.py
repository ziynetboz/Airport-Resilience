"""
On-Time Performance (OTP) versus the published flight schedule (STA / STD).
"""

from typing import Iterable

from agents.flight import Flight, FlightType, FlightState


def compute_otp_metrics(
    flights: Iterable[Flight],
    on_time_tolerance_steps: int,
) -> dict:
    """
    OTP for arrivals (ATA vs STA) and departures (ATD vs STD).

    A movement is on-time when actual time minus scheduled time is at most
    ``on_time_tolerance_steps`` (discrete-time analog of industry OTP15 when
    one step maps to a fixed block of minutes).
    """
    tol = on_time_tolerance_steps
    arrivals = [
        f
        for f in flights
        if f.flight_type == FlightType.ARRIVAL
        and f.actual_arrival_step is not None
        and f.state != FlightState.CANCELLED
    ]
    departures = [
        f
        for f in flights
        if f.flight_type == FlightType.DEPARTURE
        and f.actual_departure_step is not None
        and f.state != FlightState.CANCELLED
    ]

    def _otp_pct(completed: list[Flight], actual_attr: str, scheduled: str) -> float | None:
        if not completed:
            return None
        on_time = sum(
            1
            for f in completed
            if getattr(f, actual_attr) - getattr(f, scheduled) <= tol
        )
        return 100.0 * on_time / len(completed)

    arr_otp = _otp_pct(arrivals, "actual_arrival_step", "scheduled_time_step")
    dep_otp = _otp_pct(departures, "actual_departure_step", "scheduled_time_step")

    def _mean_delay(completed: list[Flight], actual_attr: str) -> float | None:
        if not completed:
            return None
        return float(
            sum(
                max(0, getattr(f, actual_attr) - f.scheduled_time_step)
                for f in completed
            )
            / len(completed)
        )

    return {
        "otp_arrival_pct": arr_otp,
        "otp_departure_pct": dep_otp,
        "arrivals_measured": len(arrivals),
        "departures_measured": len(departures),
        "mean_arrival_delay_steps": _mean_delay(arrivals, "actual_arrival_step"),
        "mean_departure_delay_steps": _mean_delay(departures, "actual_departure_step"),
        "otp_on_time_tolerance_steps": tol,
    }
