"""
Weather-related constants: capacity and cancellation by condition.
Parameterization could be moved to config if you want these tunable.
"""

from enum import Enum


class WeatherCondition(Enum):
    CLEAR = "clear"
    LIGHT_RAIN = "light_rain"
    HEAVY_RAIN = "heavy_rain"
    FOG = "fog"
    WIND = "wind"
    STORM = "storm"


# Runway capacity multiplier: 1.0 = full capacity, 0.0 = no operations
WEATHER_CAPACITY = {
    WeatherCondition.CLEAR: 1.0,
    WeatherCondition.LIGHT_RAIN: 0.85,
    WeatherCondition.HEAVY_RAIN: 0.6,
    WeatherCondition.FOG: 0.5,
    WeatherCondition.WIND: 0.7,
    WeatherCondition.STORM: 0.2,
}

# Cancellation probability per time step
WEATHER_CANCEL_PROB = {
    WeatherCondition.CLEAR: 0.0,
    WeatherCondition.LIGHT_RAIN: 0.01,
    WeatherCondition.HEAVY_RAIN: 0.05,
    WeatherCondition.FOG: 0.03,
    WeatherCondition.WIND: 0.02,
    WeatherCondition.STORM: 0.15,
}
