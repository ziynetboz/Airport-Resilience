"""
Gate and stand inventory: preferential, common-use, and remote stands.
"""

from typing import TYPE_CHECKING, Optional

from .gate_class import (
    AircraftType,
    GateClass,
    GateUseType,
    gate_compatible,
)

if TYPE_CHECKING:
    from .flight import Flight


class Gate:
    """
    A contact gate or remote stand.

    Preferential gates have an airline with first rights; common-use and
    remote stands have airline_id = None.
    """

    def __init__(
        self,
        gate_id: int,
        use_type: GateUseType,
        gate_class: GateClass,
        airline_id: Optional[int] = None,
    ):
        self.gate_id = gate_id
        self.use_type = use_type
        self.gate_class = gate_class
        self.airline_id = airline_id  # preferential airline, else None
        self.occupied_by: "Flight | None" = None
        # Gate buffer: earliest step the stand may be reassigned after release
        self.available_from_step: int = 0

    @property
    def is_available(self) -> bool:
        return self.occupied_by is None

    def is_available_at(self, step: int) -> bool:
        return self.occupied_by is None and step >= self.available_from_step


class GatePool:
    """
    Contact gates (preferential + common-use) and remote stands.

    Preferential counts come from ``gates_per_airline``. Any remainder of
    ``n_gates`` after preferential allocation becomes **common-use**.
    ``n_remote_stands`` are additional hardstands with bus transfer time.
    """

    def __init__(
        self,
        n_gates: int,
        n_airlines: int,
        gates_per_airline: "tuple[int, ...] | None" = None,
        n_remote_stands: int = 0,
        widebody_gate_share: float = 0.25,
        gate_buffer_steps: int = 0,
    ):
        self.n_airlines = n_airlines
        self.gate_buffer_steps = gate_buffer_steps
        self.gates: list[Gate] = []
        self.preferential_gates: dict[int, list[Gate]] = {i: [] for i in range(n_airlines)}
        self.common_use_gates: list[Gate] = []
        self.remote_stands: list[Gate] = []

        # Legacy attribute for code that still inspects airline pools
        self._airline_gates = self.preferential_gates

        preferential_counts = self._resolve_preferential_counts(
            n_gates, n_airlines, gates_per_airline
        )
        n_preferential = sum(preferential_counts)
        if n_preferential > n_gates:
            raise ValueError(
                f"gates_per_airline sum ({n_preferential}) exceeds n_gates ({n_gates})"
            )
        n_common = n_gates - n_preferential

        gid = 0
        for airline_id, count in enumerate(preferential_counts):
            classes = self._assign_gate_classes(count, widebody_gate_share)
            for i in range(count):
                gate = Gate(
                    gate_id=gid,
                    use_type=GateUseType.PREFERENTIAL,
                    gate_class=classes[i],
                    airline_id=airline_id,
                )
                self.gates.append(gate)
                self.preferential_gates[airline_id].append(gate)
                gid += 1

        common_classes = self._assign_gate_classes(n_common, widebody_gate_share)
        for i in range(n_common):
            gate = Gate(
                gate_id=gid,
                use_type=GateUseType.COMMON_USE,
                gate_class=common_classes[i],
                airline_id=None,
            )
            self.gates.append(gate)
            self.common_use_gates.append(gate)
            gid += 1

        remote_classes = self._assign_gate_classes(
            n_remote_stands, widebody_gate_share
        )
        for i in range(n_remote_stands):
            gate = Gate(
                gate_id=gid,
                use_type=GateUseType.REMOTE_STAND,
                gate_class=remote_classes[i],
                airline_id=None,
            )
            self.gates.append(gate)
            self.remote_stands.append(gate)
            gid += 1

    @staticmethod
    def _resolve_preferential_counts(
        n_gates: int,
        n_airlines: int,
        gates_per_airline: "tuple[int, ...] | None",
    ) -> list[int]:
        if gates_per_airline is not None and len(gates_per_airline) == n_airlines:
            return list(gates_per_airline)
        # Equal preferential split leaving ~20% common-use when possible
        preferential_budget = max(n_airlines, int(n_gates * 0.8))
        base = preferential_budget // n_airlines
        rem = preferential_budget % n_airlines
        return [base + (1 if i < rem else 0) for i in range(n_airlines)]

    @staticmethod
    def _assign_gate_classes(n: int, widebody_share: float) -> list[GateClass]:
        if n <= 0:
            return []
        n_wide = max(0, min(n, int(round(n * widebody_share))))
        classes = [GateClass.WIDEBODY] * n_wide + [GateClass.NARROWBODY] * (n - n_wide)
        return classes

    def request_gate(self, airline_id: int) -> "Gate | None":
        """
        Legacy API: preferential only, narrowbody-compatible (any gate class).
        Prefer ``GateAllocator.assign``.
        """
        for gate in self.preferential_gates.get(airline_id, []):
            if gate.is_available:
                return gate
        return None

    def release_gate(self, flight: "Flight", current_step: int = 0) -> None:
        """Release the stand and start the gate buffer clock."""
        for gate in self.gates:
            if gate.occupied_by is flight:
                gate.occupied_by = None
                gate.available_from_step = current_step + self.gate_buffer_steps
                return

    def find_available(
        self,
        candidates: list[Gate],
        aircraft_type: AircraftType,
        step: int,
    ) -> Optional[Gate]:
        for gate in candidates:
            if gate.is_available_at(step) and gate_compatible(
                gate.gate_class, aircraft_type
            ):
                return gate
        return None

    def gates_available_for_airline(self, airline_id: int) -> int:
        return sum(
            1 for g in self.preferential_gates.get(airline_id, []) if g.is_available
        )

    def total_available(self) -> int:
        """Available contact gates + remote stands."""
        return sum(1 for g in self.gates if g.is_available)

    def contact_gates_available(self) -> int:
        return sum(
            1
            for g in self.gates
            if g.use_type != GateUseType.REMOTE_STAND and g.is_available
        )
