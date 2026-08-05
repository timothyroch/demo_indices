"""
Humidex calculation using the standard Environment Canada / Wikipedia formula.

    e = 6.11 × exp(5417.7530 × (1/273.16 − 1/T_dew_K))
    Humidex = T_air + 0.5555 × (e − 10.0)

This is a pure utility function with no dependencies — reusable by any module.
"""

import math


def compute_humidex(t_air_c: float, dew_point_c: float) -> float:
    """Compute the Humidex value from air temperature and dew point.

    Args:
        t_air_c: Air temperature in degrees Celsius.
        dew_point_c: Dew point temperature in degrees Celsius.

    Returns:
        Humidex value (dimensionless, but expressed in "Humidex units").
    """
    t_dew_k = dew_point_c + 273.15
    e = 6.11 * math.exp(5417.7530 * (1.0 / 273.16 - 1.0 / t_dew_k))
    return round(t_air_c + 0.5555 * (e - 10.0), 1)
