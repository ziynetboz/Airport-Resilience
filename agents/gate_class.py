"""
Gate and aircraft type classes used for compatibility matching.

Industry terms:
- narrowbody / widebody aircraft types
- contact gate vs remote stand (hardstand)
- preferential use vs common-use gates
"""

from enum import Enum


class AircraftType(str, Enum):
    NARROWBODY = "narrowbody"
    WIDEBODY = "widebody"


class GateClass(str, Enum):
    """Physical capability of a stand/gate."""

    NARROWBODY = "narrowbody"
    WIDEBODY = "widebody"


class GateUseType(str, Enum):
    """How the stand is leased / controlled."""

    PREFERENTIAL = "preferential"
    COMMON_USE = "common_use"
    REMOTE_STAND = "remote_stand"


def gate_compatible(gate_class: GateClass, aircraft_type: AircraftType) -> bool:
    """
    Widebody gates accept narrowbody and widebody.
    Narrowbody gates accept narrowbody only.
    """
    if gate_class == GateClass.WIDEBODY:
        return True
    return aircraft_type == AircraftType.NARROWBODY
