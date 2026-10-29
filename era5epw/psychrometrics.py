"""Psychrometric functions for moist air.

Equations are taken from the ASHRAE Handbook - Fundamentals (2017), chapter 1, in SI units.
All functions accept scalars or numpy arrays.

Units: temperatures in °C, relative humidity in %, pressures in Pa, humidity ratio in kg of
water per kg of dry air, enthalpy in kJ/kg of dry air, specific volume in m³/kg of dry air.
"""

from collections.abc import Callable

import numpy as np

# Standard atmospheric pressure at sea level (Pa)
STANDARD_ATMOSPHERIC_PRESSURE = 101325.0

# Ratio of molecular weights of water vapor and dry air
_MOLECULAR_WEIGHT_RATIO = 0.621945


def _bisect(
    func: Callable[[np.ndarray], np.ndarray],
    lower: np.ndarray,
    upper: np.ndarray,
    iterations: int = 60,
) -> np.ndarray:
    """Find the root of an increasing function by vectorized bisection.

    :param func: Increasing function, negative at `lower` and positive at `upper`.
    :param lower: Lower bounds of the search intervals.
    :param upper: Upper bounds of the search intervals.
    :param iterations: Number of bisection iterations.
    :return: Roots of the function, clipped to the search intervals.
    """
    lower, upper = np.broadcast_arrays(
        np.asarray(lower, dtype=float), np.asarray(upper, dtype=float)
    )
    lower, upper = lower.copy(), upper.copy()
    for _ in range(iterations):
        middle = (lower + upper) / 2
        positive = func(middle) > 0
        upper = np.where(positive, middle, upper)
        lower = np.where(positive, lower, middle)
    return (lower + upper) / 2


def saturation_vapor_pressure(t: np.ndarray | float) -> np.ndarray:
    """Saturation pressure of water vapor over ice (t < 0°C) or liquid water (t >= 0°C).

    :param t: Dry bulb temperature (°C).
    :return: Saturation vapor pressure (Pa).
    """
    t_k = np.asarray(t, dtype=float) + 273.15
    over_ice = np.exp(
        -5.6745359e03 / t_k
        + 6.3925247
        - 9.6778430e-03 * t_k
        + 6.2215701e-07 * t_k**2
        + 2.0747825e-09 * t_k**3
        - 9.4840240e-13 * t_k**4
        + 4.1635019 * np.log(t_k)
    )
    over_water = np.exp(
        -5.8002206e03 / t_k
        + 1.3914993
        - 4.8640239e-02 * t_k
        + 4.1764768e-05 * t_k**2
        - 1.4452093e-08 * t_k**3
        + 6.5459673 * np.log(t_k)
    )
    return np.where(t_k < 273.15, over_ice, over_water)


def vapor_pressure_from_relative_humidity(
    t: np.ndarray | float, rh: np.ndarray | float
) -> np.ndarray:
    """Partial pressure of water vapor in moist air.

    :param t: Dry bulb temperature (°C).
    :param rh: Relative humidity (%).
    :return: Partial vapor pressure (Pa).
    """
    return np.asarray(rh, dtype=float) / 100 * saturation_vapor_pressure(t)


def humidity_ratio_from_vapor_pressure(
    pw: np.ndarray | float, p: np.ndarray | float = STANDARD_ATMOSPHERIC_PRESSURE
) -> np.ndarray:
    """Humidity ratio of moist air.

    :param pw: Partial vapor pressure (Pa).
    :param p: Atmospheric pressure (Pa).
    :return: Humidity ratio (kg/kg dry air).
    """
    pw = np.asarray(pw, dtype=float)
    return _MOLECULAR_WEIGHT_RATIO * pw / (np.asarray(p, dtype=float) - pw)


def saturation_humidity_ratio(
    t: np.ndarray | float, p: np.ndarray | float = STANDARD_ATMOSPHERIC_PRESSURE
) -> np.ndarray:
    """Humidity ratio of saturated moist air.

    :param t: Dry bulb temperature (°C).
    :param p: Atmospheric pressure (Pa).
    :return: Saturation humidity ratio (kg/kg dry air).
    """
    return humidity_ratio_from_vapor_pressure(saturation_vapor_pressure(t), p)


def moist_air_enthalpy(t: np.ndarray | float, w: np.ndarray | float) -> np.ndarray:
    """Specific enthalpy of moist air.

    :param t: Dry bulb temperature (°C).
    :param w: Humidity ratio (kg/kg dry air).
    :return: Enthalpy (kJ/kg dry air).
    """
    t = np.asarray(t, dtype=float)
    return 1.006 * t + np.asarray(w, dtype=float) * (2501 + 1.86 * t)


def humidity_ratio_from_enthalpy(h: np.ndarray | float, t: np.ndarray | float) -> np.ndarray:
    """Humidity ratio of moist air with a given enthalpy and dry bulb temperature.

    :param h: Enthalpy (kJ/kg dry air).
    :param t: Dry bulb temperature (°C).
    :return: Humidity ratio (kg/kg dry air).
    """
    t = np.asarray(t, dtype=float)
    return (np.asarray(h, dtype=float) - 1.006 * t) / (2501 + 1.86 * t)


def moist_air_specific_volume(
    t: np.ndarray | float,
    w: np.ndarray | float,
    p: np.ndarray | float = STANDARD_ATMOSPHERIC_PRESSURE,
) -> np.ndarray:
    """Specific volume of moist air.

    :param t: Dry bulb temperature (°C).
    :param w: Humidity ratio (kg/kg dry air).
    :param p: Atmospheric pressure (Pa).
    :return: Specific volume (m³/kg dry air).
    """
    t_k = np.asarray(t, dtype=float) + 273.15
    w = np.asarray(w, dtype=float)
    return 0.287042 * t_k * (1 + 1.607858 * w) / (np.asarray(p, dtype=float) / 1000)


def saturation_temperature_from_enthalpy(
    h: np.ndarray | float,
    p: np.ndarray | float = STANDARD_ATMOSPHERIC_PRESSURE,
    t_min: float = -100.0,
    t_max: float = 60.0,
) -> np.ndarray:
    """Dry bulb temperature of saturated moist air with a given enthalpy.

    :param h: Enthalpy (kJ/kg dry air).
    :param p: Atmospheric pressure (Pa).
    :param t_min: Lower bound of the temperature search interval (°C).
    :param t_max: Upper bound of the temperature search interval (°C).
    :return: Saturation temperature (°C), clipped to [t_min, t_max].
    """
    h = np.asarray(h, dtype=float)
    return _bisect(
        lambda t: moist_air_enthalpy(t, saturation_humidity_ratio(t, p)) - h,
        np.full_like(h, t_min),
        np.full_like(h, t_max),
    )


def wet_bulb_temperature(
    t: np.ndarray | float,
    w: np.ndarray | float,
    p: np.ndarray | float = STANDARD_ATMOSPHERIC_PRESSURE,
) -> np.ndarray:
    """Thermodynamic wet bulb temperature of moist air.

    :param t: Dry bulb temperature (°C).
    :param w: Humidity ratio (kg/kg dry air).
    :param p: Atmospheric pressure (Pa).
    :return: Wet bulb temperature (°C).
    """
    t, w, p = np.broadcast_arrays(
        np.asarray(t, dtype=float), np.asarray(w, dtype=float), np.asarray(p, dtype=float)
    )

    def humidity_ratio_at_wet_bulb(t_wb: np.ndarray) -> np.ndarray:
        ws_wb = saturation_humidity_ratio(t_wb, p)
        over_water = ((2501 - 2.326 * t_wb) * ws_wb - 1.006 * (t - t_wb)) / (
            2501 + 1.86 * t - 4.186 * t_wb
        )
        over_ice = ((2830 - 0.24 * t_wb) * ws_wb - 1.006 * (t - t_wb)) / (
            2830 + 1.86 * t - 2.1 * t_wb
        )
        return np.where(t_wb >= 0, over_water, over_ice) - w

    return _bisect(humidity_ratio_at_wet_bulb, np.full_like(t, -100.0), t)
