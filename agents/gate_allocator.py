"""
Gate assignment policy: preferential → common-use → remote stand.

Industry practice for hybrid preferential / common-use airports.
"""

from typing import TYPE_CHECKING, Optional

from agents.gate import Gate
from agents.gate_class import AircraftType, GateUseType

if TYPE_CHECKING:
    from model.abm import AirportABM
    from agents.flight import Flight


class GateAllocator:
    """
    Assign stands in priority order:

    1. Preferential gate for the operating airline (compatible class)
    2. Common-use contact gate
    3. Remote stand (hardstand; bus transfer applies)
    4. None → gate hold (flight waits)
    """

    def __init__(self, model: "AirportABM"):
        self.model = model
        self.preferential_assignments = 0
        self.common_use_assignments = 0
        self.remote_stand_assignments = 0
        self.gate_holds = 0
        # Per-step counters (reset in step())
        self.preferential_this_step = 0
        self.common_use_this_step = 0
        self.remote_stand_this_step = 0
        self.gate_holds_this_step = 0

    def step(self) -> None:
        self.preferential_this_step = 0
        self.common_use_this_step = 0
        self.remote_stand_this_step = 0
        self.gate_holds_this_step = 0

    def assign(
        self,
        airline_id: int,
        aircraft_type: AircraftType,
    ) -> Optional[Gate]:
        pool = self.model.airport.gate_pool
        step = self.model.steps

        gate = pool.find_available(
            pool.preferential_gates.get(airline_id, []),
            aircraft_type,
            step,
        )
        if gate is not None:
            self._record(GateUseType.PREFERENTIAL)
            return gate

        gate = pool.find_available(pool.common_use_gates, aircraft_type, step)
        if gate is not None:
            self._record(GateUseType.COMMON_USE)
            return gate

        gate = pool.find_available(pool.remote_stands, aircraft_type, step)
        if gate is not None:
            self._record(GateUseType.REMOTE_STAND)
            return gate

        self.gate_holds += 1
        self.gate_holds_this_step += 1
        return None

    def _record(self, use_type: GateUseType) -> None:
        if use_type == GateUseType.PREFERENTIAL:
            self.preferential_assignments += 1
            self.preferential_this_step += 1
        elif use_type == GateUseType.COMMON_USE:
            self.common_use_assignments += 1
            self.common_use_this_step += 1
        elif use_type == GateUseType.REMOTE_STAND:
            self.remote_stand_assignments += 1
            self.remote_stand_this_step += 1
