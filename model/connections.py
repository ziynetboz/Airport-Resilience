"""
Connecting-passenger itineraries and Minimum Connection Time (MCT).

Links a share of inbound passengers to a later outbound flight on a
feasible connection (scheduled STD >= STA + MCT), preferring same airline.
"""

import random
from typing import TYPE_CHECKING, List, Optional

from agents.flight import Flight, FlightType
from agents.passenger_type import PassengerType
from agents.traveler import Traveler, TravelerState

if TYPE_CHECKING:
    from model.abm import AirportABM
    from config.schema import SimulationConfig


def find_connecting_departure(
    inbound: Flight,
    outbound_candidates: List[Flight],
    mct_steps: int,
) -> Optional[Flight]:
    """
    Pick an outbound with STD >= STA + MCT.

    Prefer same airline; otherwise any feasible departure.
    """
    earliest = inbound.scheduled_time_step + mct_steps
    same_airline = [
        f
        for f in outbound_candidates
        if f.airline_id == inbound.airline_id
        and f.scheduled_time_step >= earliest
        and f.state.name != "CANCELLED"
    ]
    if same_airline:
        return min(same_airline, key=lambda f: f.scheduled_time_step)
    any_airline = [
        f
        for f in outbound_candidates
        if f.scheduled_time_step >= earliest and f.state.name != "CANCELLED"
    ]
    if any_airline:
        return min(any_airline, key=lambda f: f.scheduled_time_step)
    return None


def create_travelers_for_rotation(
    model: "AirportABM",
    config: "SimulationConfig",
    inbound: Flight,
    outbound: Flight,
    pax_in: int,
    pax_out: int,
    all_outbounds: List[Flight],
) -> None:
    """
    Create terminating / connecting passengers for the inbound leg and
    originating passengers for the outbound leg.
    """
    mct = config.mct_steps
    n_connecting = int(round(pax_in * config.connecting_passenger_share))
    n_connecting = max(0, min(pax_in, n_connecting))
    n_terminating = pax_in - n_connecting

    for _ in range(n_terminating):
        t = Traveler(
            model,
            arrival_flight=inbound,
            departure_flight=None,
            passenger_type=PassengerType.TERMINATING,
        )
        model.travelers.append(t)

    for _ in range(n_connecting):
        dep = find_connecting_departure(inbound, all_outbounds, mct)
        if dep is None:
            # No feasible connection: treat as terminating
            t = Traveler(
                model,
                arrival_flight=inbound,
                departure_flight=None,
                passenger_type=PassengerType.TERMINATING,
            )
        else:
            t = Traveler(
                model,
                arrival_flight=inbound,
                departure_flight=dep,
                passenger_type=PassengerType.CONNECTING,
            )
            t.mct_steps = mct
        model.travelers.append(t)

    # Originating: local departures on this outbound (do not double-count connectors)
    # Cap originating so outbound load stays near pax_out
    connectors_on_this = sum(
        1
        for t in model.travelers
        if t.departure_flight is outbound
        and t.passenger_type == PassengerType.CONNECTING
    )
    n_originating = max(0, pax_out - connectors_on_this)
    for _ in range(n_originating):
        t = Traveler(
            model,
            arrival_flight=None,
            departure_flight=outbound,
            passenger_type=PassengerType.ORIGINATING,
        )
        t.state = TravelerState.IN_TERMINAL
        t.entered_terminal_at = max(
            1, outbound.scheduled_time_step - random.randint(1, 20)
        )
        model.travelers.append(t)
