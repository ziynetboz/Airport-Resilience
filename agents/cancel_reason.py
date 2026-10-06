"""
Cancel reason codes for irregular operations (IROPS).
Uses standard industry framing: airlines cancel; ATC/weather constrain capacity.
"""

from enum import Enum


class CancelReason(str, Enum):
    """Who/why a flight was cancelled (not airport-initiated flight cancellations)."""

    AIRLINE_IROPS = "airline_irops"
    # Reserved for later phases (crew, maintenance, diversion follow-on, etc.)
