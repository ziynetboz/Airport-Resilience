"""
Build a published flight schedule with aircraft rotations (STA / STD / MGT).
"""

import random
from typing import TYPE_CHECKING, List

from agents.aircraft import Aircraft
from agents.flight import Flight, FlightType
from agents.traveler import Traveler, TravelerState
from agents.gate_class import AircraftType
from model.inbound_delay import draw_inbound_delay_steps

if TYPE_CHECKING:
    from model.abm import AirportABM
    from config.schema import SimulationConfig


def _draw_aircraft_type(config: "SimulationConfig") -> AircraftType:
    if random.random() < config.widebody_share:
        return AircraftType.WIDEBODY
    return AircraftType.NARROWBODY


def build_published_rotations(
    model: "AirportABM",
    config: "SimulationConfig",
) -> List[Aircraft]:
    """
    Pre-build inbound and outbound legs paired on the same aircraft registration.

    - STA (Scheduled Time of Arrival) and STD (Scheduled Time of Departure) are
      step indices in the published schedule.
    - STD is at least STA + min_ground_time_steps (MGT).
    - Inbound and outbound share the same aircraft type (narrowbody / widebody).
    """
    n_airlines = config.n_airlines
    shares = config.airline_flight_share
    if shares is None or len(shares) != n_airlines:
        weights = None
    else:
        weights = list(shares)

    target_movements = max(2, int(config.n_steps * config.flights_per_step))
    n_rotations = max(1, target_movements // 2)
    mgt = config.min_ground_time_steps
    horizon = max(2, config.n_steps - mgt - 1)

    rotations: List[Aircraft] = []
    for i in range(n_rotations):
        sta = 1 + int(i * (horizon - 1) / max(1, n_rotations - 1)) if n_rotations > 1 else 1
        std = min(config.n_steps - 1, sta + mgt)
        airline_id = (
            random.choices(range(n_airlines), weights=weights, k=1)[0]
            if weights
            else random.randint(0, n_airlines - 1)
        )
        aircraft_type = _draw_aircraft_type(config)
        pax_in = random.randint(
            config.passengers_per_flight[0],
            config.passengers_per_flight[1],
        )
        pax_out = random.randint(
            config.passengers_per_flight[0],
            config.passengers_per_flight[1],
        )

        inbound = Flight(
            model,
            FlightType.ARRIVAL,
            scheduled_step=sta,
            passenger_count=pax_in,
            airline_id=airline_id,
            aircraft_type=aircraft_type,
        )
        inbound.scheduled_time_step = sta
        inbound_delay = draw_inbound_delay_steps(config)
        inbound.inbound_delay_steps = inbound_delay
        inbound.eta_step = sta + inbound_delay

        outbound = Flight(
            model,
            FlightType.DEPARTURE,
            scheduled_step=std,
            passenger_count=pax_out,
            airline_id=airline_id,
            aircraft_type=aircraft_type,
        )
        outbound.scheduled_time_step = std

        ac = Aircraft(airline_id, inbound, outbound)
        inbound.aircraft_registration = ac.registration
        outbound.aircraft_registration = ac.registration
        inbound.aircraft = ac
        outbound.aircraft = ac

        model.flights.extend([inbound, outbound])
        _create_travelers(model, inbound, outbound, pax_in, pax_out, sta, std)
        rotations.append(ac)

    return rotations


def _create_travelers(
    model: "AirportABM",
    inbound: Flight,
    outbound: Flight,
    pax_in: int,
    pax_out: int,
    sta: int,
    std: int,
) -> None:
    for _ in range(pax_in):
        t = Traveler(model, arrival_flight=inbound)
        model.travelers.append(t)
    for _ in range(pax_out):
        t = Traveler(model, arrival_flight=None, departure_flight=outbound)
        t.state = TravelerState.IN_TERMINAL
        t.entered_terminal_at = max(1, sta - random.randint(1, 20))
        model.travelers.append(t)
