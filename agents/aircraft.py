"""
Aircraft on an airport rotation (inbound leg + outbound leg on the same registration).
"""

from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .flight import Flight


class Aircraft:
    """
    One airframe executing a rotation: arrival (STA) then departure (STD)
    after minimum ground time (MGT) on the ramp/gate.
    """

    _next_seq = 0

    def __init__(
        self,
        airline_id: int,
        inbound_flight: "Flight",
        outbound_flight: "Flight",
        registration: Optional[str] = None,
    ):
        Aircraft._next_seq += 1
        self.registration = registration or f"N{10000 + Aircraft._next_seq:05d}"
        self.airline_id = airline_id
        self.inbound_flight = inbound_flight
        self.outbound_flight = outbound_flight
        self.inbound_released = False
        self.outbound_released = False
        self.inbound_on_block_step: Optional[int] = None
        self.turnaround_ready_step: Optional[int] = None

    def record_inbound_on_block(self, step: int, min_ground_time_steps: int) -> None:
        """Inbound flight completed at gate (on-block); start MGT clock."""
        self.inbound_on_block_step = step
        self.turnaround_ready_step = step + min_ground_time_steps

    def outbound_may_start(self, current_step: int) -> bool:
        """True when STD reached and MGT satisfied (off-block may begin)."""
        if self.turnaround_ready_step is None:
            return False
        std = self.outbound_flight.scheduled_time_step
        return current_step >= std and current_step >= self.turnaround_ready_step
