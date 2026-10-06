"""
Baggage handling: unload, transfer, make-up, claim, and departure bag readiness.
"""

from typing import TYPE_CHECKING, List

from agents.bag_types import BagType, BagState
from agents.baggage import BagBatch
from agents.passenger_type import PassengerType
from agents.flight import Flight

if TYPE_CHECKING:
    from model.abm import AirportABM
    from config.schema import SimulationConfig


class BaggageHandling:
    """
    Airport baggage system.

    - Local originating: check-in → make-up → loaded
    - Transfer: inbound unload → transfer → make-up → loaded
    - Local terminating: unload → claim
    - Optional: hold departure pushback until bags are loaded or mishandled
    """

    def __init__(self, model: "AirportABM"):
        self.model = model
        self.batches: List[BagBatch] = []
        self.mishandled_bags_this_step = 0
        self.mishandled_bags_total = 0
        self.bag_holds_this_step = 0
        self.bag_holds_total = 0
        self.bags_loaded_this_step = 0
        self.bags_claimed_this_step = 0

    def step(self) -> None:
        self.mishandled_bags_this_step = 0
        self.bag_holds_this_step = 0
        self.bags_loaded_this_step = 0
        self.bags_claimed_this_step = 0
        if not self.model._config.baggage_enabled:
            return
        for batch in self.batches:
            before = batch.state
            batch.step()
            if before != BagState.LOADED and batch.state == BagState.LOADED:
                self.bags_loaded_this_step += batch.bag_count
            if before != BagState.CLAIMED and batch.state == BagState.CLAIMED:
                self.bags_claimed_this_step += batch.bag_count

    def departure_bags_ready(self, flight: Flight) -> bool:
        """
        True if all bags for this departure are LOADED or already MISHANDLED
        (left behind), so pushback may proceed.
        """
        if not self.model._config.baggage_enabled:
            return True
        if not self.model._config.bag_hold_departure:
            return True
        pending = False
        for batch in self.batches:
            if batch.departure_flight is not flight:
                continue
            if batch.state == BagState.LOADED:
                continue
            if batch.state == BagState.MISHANDLED:
                continue
            pending = True
            break
        if pending:
            self.bag_holds_this_step += 1
            self.bag_holds_total += 1
            return False
        return True

    def bags_in_process(self) -> int:
        active = {
            BagState.CHECKED_IN,
            BagState.ON_INBOUND_AIRCRAFT,
            BagState.UNLOADING,
            BagState.IN_TRANSFER,
            BagState.AT_MAKE_UP,
            BagState.AT_CLAIM,
        }
        return sum(b.bag_count for b in self.batches if b.state in active)

    def transfer_success_count(self) -> int:
        return sum(
            b.bag_count
            for b in self.batches
            if b.bag_type == BagType.TRANSFER and b.state == BagState.LOADED
        )

    def transfer_mishandled_count(self) -> int:
        return sum(
            b.bag_count
            for b in self.batches
            if b.bag_type == BagType.TRANSFER and b.state == BagState.MISHANDLED
        )


def create_baggage_from_travelers(
    model: "AirportABM",
    config: "SimulationConfig",
) -> None:
    """Create bag batches from passenger itineraries."""
    if not config.baggage_enabled:
        return
    rate = config.bags_per_passenger
    # Aggregate counts by (type, arrival, departure)
    key_counts: dict[tuple, int] = {}

    for t in model.travelers:
        n_bags = max(0, int(round(rate)))
        if n_bags <= 0:
            continue
        if t.passenger_type == PassengerType.ORIGINATING and t.departure_flight:
            key = (BagType.LOCAL_ORIGINATING, None, t.departure_flight)
        elif t.passenger_type == PassengerType.TERMINATING and t.arrival_flight:
            key = (BagType.LOCAL_TERMINATING, t.arrival_flight, None)
        elif t.passenger_type == PassengerType.CONNECTING and t.arrival_flight and t.departure_flight:
            key = (BagType.TRANSFER, t.arrival_flight, t.departure_flight)
        else:
            continue
        key_counts[key] = key_counts.get(key, 0) + n_bags

    for (bag_type, arr, dep), count in key_counts.items():
        batch = BagBatch(
            model,
            bag_type=bag_type,
            bag_count=count,
            arrival_flight=arr,
            departure_flight=dep,
        )
        model.baggage_handling.batches.append(batch)
        model.bags.append(batch)


def create_baggage_for_stochastic_flight(
    model: "AirportABM",
    flight: Flight,
    is_arrival: bool,
    passenger_count: int,
) -> None:
    """Simple local bags for stochastic schedule mode."""
    if not model._config.baggage_enabled:
        return
    n_bags = max(0, int(round(passenger_count * model._config.bags_per_passenger)))
    if n_bags <= 0:
        return
    if is_arrival:
        batch = BagBatch(
            model,
            BagType.LOCAL_TERMINATING,
            n_bags,
            arrival_flight=flight,
        )
    else:
        batch = BagBatch(
            model,
            BagType.LOCAL_ORIGINATING,
            n_bags,
            departure_flight=flight,
        )
    model.baggage_handling.batches.append(batch)
    model.bags.append(batch)
