"""
Weather agent: environmental conditions and natural shock events.
"""

import random
from typing import TYPE_CHECKING

from .weather_constants import (
    WeatherCondition,
    WEATHER_CAPACITY,
    WEATHER_CANCEL_PROB,
)

if TYPE_CHECKING:
    from model.abm import AirportABM


class WeatherAgent:
    """
    Governs weather state and shock events.
    Shocks reduce runway capacity and increase cancellations.
    """

    def __init__(
        self,
        model: "AirportABM",
        shock_at_step: int | None = None,
        shock_duration: int = 12,
        normal_variation_prob: float = 0.02,
    ):
        self.model = model
        self.condition = WeatherCondition.CLEAR
        self.shock_at_step = shock_at_step
        self.shock_duration = shock_duration
        self.normal_variation_prob = normal_variation_prob
        self.shock_start_step: int | None = None
        self._steps_in_shock = 0

    def step(self) -> None:
        """Update weather; start/end shock at configured steps."""
        if (
            self.shock_at_step is not None
            and self.model.steps == self.shock_at_step
        ):
            self._start_shock()
        if self.condition == WeatherCondition.STORM:
            self._steps_in_shock += 1
            if self._steps_in_shock >= self.shock_duration:
                self._end_shock()
        else:
            if random.random() < self.normal_variation_prob:
                self.condition = random.choice([
                    WeatherCondition.CLEAR,
                    WeatherCondition.LIGHT_RAIN,
                    WeatherCondition.WIND,
                ])

    def _start_shock(self) -> None:
        self.condition = WeatherCondition.STORM
        self.shock_start_step = self.model.steps
        self._steps_in_shock = 0

    def _end_shock(self) -> None:
        self.condition = WeatherCondition.CLEAR
        self.shock_start_step = None
        self._steps_in_shock = 0

    def capacity_factor(self) -> float:
        """Runway capacity multiplier in [0, 1]."""
        return WEATHER_CAPACITY.get(self.condition, 1.0)

    def cancel_probability(self) -> float:
        """
        Legacy weather cancel probability.

        Unused for flight cancellations as of Phase B: airlines cancel under
        IROPS; weather only reduces capacity (and can trigger GDP).
        """
        return WEATHER_CANCEL_PROB.get(self.condition, 0.0)

    def is_shock(self) -> bool:
        return self.condition == WeatherCondition.STORM
