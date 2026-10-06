"""
Passenger itinerary types (industry: originating, terminating, connecting).
"""

from enum import Enum


class PassengerType(str, Enum):
    """How the passenger uses the airport in this itinerary segment."""

    ORIGINATING = "originating"  # local departure (starts in terminal)
    TERMINATING = "terminating"  # local arrival (exits after inbound)
    CONNECTING = "connecting"  # transfer: inbound then outbound
