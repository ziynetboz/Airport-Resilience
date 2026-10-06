"""
Bag batch: a group of bags on the same itinerary path.

Using batches (not one agent per bag) keeps the ABM tractable while
tracking transfer, make-up, claim, and mishandled outcomes.
"""

from typing import TYPE_CHECKING, Optional

from agents.bag_types import BagType, BagState

if TYPE_CHECKING:
    from model.abm import AirportABM
    from agents.flight import Flight


class BagBatch:
    """Bags sharing the same type and inbound/outbound flights."""

    _next_id = 0

    def __init__(
        self,
        model: "AirportABM",
        bag_type: BagType,
        bag_count: int,
        arrival_flight: "Flight | None" = None,
        departure_flight: "Flight | None" = None,
    ):
        BagBatch._next_id += 1
        self.unique_id = f"bagbatch_{BagBatch._next_id}"
        self.model = model
        self.bag_type = bag_type
        self.bag_count = max(0, bag_count)
        self.arrival_flight = arrival_flight
        self.departure_flight = departure_flight
        self.steps_remaining = 0
        self.mishandled = False

        if bag_type == BagType.LOCAL_ORIGINATING:
            self.state = BagState.CHECKED_IN
        elif bag_type in (BagType.TRANSFER, BagType.LOCAL_TERMINATING):
            self.state = BagState.ON_INBOUND_AIRCRAFT
        else:
            self.state = BagState.CHECKED_IN

    def step(self) -> None:
        if self.bag_count <= 0:
            return
        if self.state in (BagState.LOADED, BagState.CLAIMED, BagState.MISHANDLED):
            return

        cfg = self.model._config
        if not cfg.baggage_enabled:
            return

        if self.bag_type == BagType.LOCAL_ORIGINATING:
            self._step_originating()
        elif self.bag_type == BagType.LOCAL_TERMINATING:
            self._step_terminating()
        elif self.bag_type == BagType.TRANSFER:
            self._step_transfer()

    def _step_originating(self) -> None:
        cfg = self.model._config
        dep = self.departure_flight
        if dep is None or dep.state.name == "CANCELLED":
            self._mark_mishandled()
            return

        if self.state == BagState.CHECKED_IN:
            # Enter make-up once the outbound is released / at gate
            if dep.state.name in ("SCHEDULED", "AT_GATE", "TAXIING_OUT", "IN_QUEUE", "COMPLETED"):
                if dep.aircraft is None or getattr(dep.aircraft, "outbound_released", True):
                    self.state = BagState.AT_MAKE_UP
                    self.steps_remaining = cfg.bag_make_up_steps
            return

        if self.state == BagState.AT_MAKE_UP:
            self.steps_remaining -= 1
            if self.steps_remaining <= 0:
                if dep.state.name in ("TAXIING_OUT", "IN_QUEUE", "COMPLETED", "CANCELLED"):
                    # Too late to load
                    if dep.state.name != "CANCELLED":
                        self._mark_mishandled()
                    else:
                        self._mark_mishandled()
                else:
                    self.state = BagState.LOADED
            return

    def _step_terminating(self) -> None:
        cfg = self.model._config
        arr = self.arrival_flight
        if arr is None or arr.state.name == "CANCELLED":
            self._mark_mishandled()
            return

        if self.state == BagState.ON_INBOUND_AIRCRAFT:
            if arr.state.name == "COMPLETED":
                self.state = BagState.UNLOADING
                self.steps_remaining = cfg.bag_unload_steps
            return

        if self.state == BagState.UNLOADING:
            self.steps_remaining -= 1
            if self.steps_remaining <= 0:
                self.state = BagState.AT_CLAIM
                self.steps_remaining = cfg.bag_claim_steps
            return

        if self.state == BagState.AT_CLAIM:
            self.steps_remaining -= 1
            if self.steps_remaining <= 0:
                self.state = BagState.CLAIMED
            return

    def _step_transfer(self) -> None:
        cfg = self.model._config
        arr = self.arrival_flight
        dep = self.departure_flight

        if arr is not None and arr.state.name == "CANCELLED":
            self._mark_mishandled()
            return
        if dep is not None and dep.state.name == "CANCELLED":
            self._mark_mishandled()
            return

        # Outbound already gone → mishandled transfer
        if dep is not None and dep.state.name in ("TAXIING_OUT", "IN_QUEUE", "COMPLETED"):
            if self.state not in (BagState.LOADED,):
                self._mark_mishandled()
                return

        if self.state == BagState.ON_INBOUND_AIRCRAFT:
            if arr is not None and arr.state.name == "COMPLETED":
                self.state = BagState.UNLOADING
                self.steps_remaining = cfg.bag_unload_steps
            return

        if self.state == BagState.UNLOADING:
            self.steps_remaining -= 1
            if self.steps_remaining <= 0:
                self.state = BagState.IN_TRANSFER
                self.steps_remaining = cfg.bag_transfer_steps
            return

        if self.state == BagState.IN_TRANSFER:
            self.steps_remaining -= 1
            if self.steps_remaining <= 0:
                self.state = BagState.AT_MAKE_UP
                self.steps_remaining = cfg.bag_make_up_steps
            return

        if self.state == BagState.AT_MAKE_UP:
            self.steps_remaining -= 1
            if self.steps_remaining <= 0:
                if dep is not None and dep.state.name in (
                    "TAXIING_OUT",
                    "IN_QUEUE",
                    "COMPLETED",
                    "CANCELLED",
                ):
                    self._mark_mishandled()
                else:
                    self.state = BagState.LOADED
            return

    def _mark_mishandled(self) -> None:
        if self.state == BagState.MISHANDLED:
            return
        self.state = BagState.MISHANDLED
        self.mishandled = True
        self.model.baggage_handling.mishandled_bags_this_step += self.bag_count
        self.model.baggage_handling.mishandled_bags_total += self.bag_count
