"""
Baggage flow types and process states (industry terms).
"""

from enum import Enum


class BagType(str, Enum):
    """How the bag moves through the airport."""

    LOCAL_ORIGINATING = "local_originating"  # check-in → make-up → load
    TRANSFER = "transfer"  # inbound unload → transfer → make-up → load
    LOCAL_TERMINATING = "local_terminating"  # unload → claim


class BagState(str, Enum):
    """Baggage handling process state."""

    CHECKED_IN = "checked_in"
    ON_INBOUND_AIRCRAFT = "on_inbound_aircraft"
    UNLOADING = "unloading"
    IN_TRANSFER = "in_transfer"
    AT_MAKE_UP = "at_make_up"
    LOADED = "loaded"
    AT_CLAIM = "at_claim"
    CLAIMED = "claimed"
    MISHANDLED = "mishandled"
