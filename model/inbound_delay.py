"""
Inbound delay: ETA (Estimated Time of Arrival) versus STA.
"""

import math
import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from config.schema import SimulationConfig


def draw_inbound_delay_steps(config: "SimulationConfig") -> int:
    """
    Draw inbound delay in steps (late aircraft / en-route / ATC).

    With probability ``inbound_delay_prob``, delay is lognormal around
    ``inbound_delay_mean_steps``; otherwise on-time (0).
    """
    if not getattr(config, "inbound_delay_enabled", True):
        return 0
    if random.random() > config.inbound_delay_prob:
        return 0
    mean = max(0.5, float(config.inbound_delay_mean_steps))
    # lognormal with median near mean * e^{-sigma^2/2}; use sigma=0.6
    sigma = 0.6
    mu = math.log(mean) - 0.5 * sigma * sigma
    delay = int(round(random.lognormvariate(mu, sigma)))
    return max(0, delay)
