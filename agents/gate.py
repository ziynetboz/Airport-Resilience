"""
Gate and airline: gate availability and airline assignments.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .flight import Flight


class Gate:
    """A single gate. Assigned to an airline. Can be occupied by a flight."""

    def __init__(self, gate_id: int, airline_id: int):
        self.gate_id = gate_id
        self.airline_id = airline_id
        self.occupied_by: "Flight | None" = None

    @property
    def is_available(self) -> bool:
        return self.occupied_by is None


class GatePool:
    """
    Pool of gates assigned to airlines.
    Each airline has a subset of gates; flights request gates from their airline.
    Supports unequal distribution (e.g. one dominant airline, two smaller).
    """

    def __init__(
        self,
        n_gates: int,
        n_airlines: int,
        gates_per_airline: "tuple[int, ...] | None" = None,
    ):
        self.gates: list[Gate] = []
        self._airline_gates: dict[int, list[Gate]] = {i: [] for i in range(n_airlines)}
        if gates_per_airline is not None and len(gates_per_airline) == n_airlines:
            # Use explicit distribution (e.g. 70, 15, 15)
            gid = 0
            for airline_id, count in enumerate(gates_per_airline):
                for _ in range(count):
                    if gid >= n_gates:
                        break
                    gate = Gate(gate_id=gid, airline_id=airline_id)
                    self.gates.append(gate)
                    self._airline_gates[airline_id].append(gate)
                    gid += 1
            # Pad if gates_per_airline sums to less than n_gates
            while len(self.gates) < n_gates:
                airline_id = len(self.gates) % n_airlines
                gate = Gate(gate_id=len(self.gates), airline_id=airline_id)
                self.gates.append(gate)
                self._airline_gates[airline_id].append(gate)
        else:
            # Equal split
            gates_per = max(1, n_gates // n_airlines)
            for gid in range(n_gates):
                airline_id = min(gid // gates_per, n_airlines - 1)
                gate = Gate(gate_id=gid, airline_id=airline_id)
                self.gates.append(gate)
                self._airline_gates[airline_id].append(gate)

    def request_gate(self, airline_id: int) -> "Gate | None":
        """Assign an available gate to the airline. Returns None if none free."""
        for gate in self._airline_gates.get(airline_id, []):
            if gate.is_available:
                return gate
        return None

    def release_gate(self, flight: "Flight") -> None:
        """Release the gate occupied by the flight."""
        for gate in self.gates:
            if gate.occupied_by is flight:
                gate.occupied_by = None
                return

    def gates_available_for_airline(self, airline_id: int) -> int:
        """Count of available gates for this airline."""
        return sum(1 for g in self._airline_gates.get(airline_id, []) if g.is_available)

    def total_available(self) -> int:
        """Total available gates across all airlines."""
        return sum(1 for g in self.gates if g.is_available)
