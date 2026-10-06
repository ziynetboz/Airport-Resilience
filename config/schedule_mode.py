"""
How demand enters the simulator.

- ``stochastic``: legacy Poisson-style injection each step (no published timetable).
- ``published``: flights follow a published flight schedule with aircraft rotations.
"""

from enum import Enum


class ScheduleMode(str, Enum):
    STOCHASTIC = "stochastic"
    PUBLISHED = "published"
