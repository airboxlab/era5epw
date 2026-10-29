"""Tests for the psychrometric functions, against ASHRAE Handbook - Fundamentals reference
values."""

import unittest

import numpy as np

from era5epw.psychrometrics import (
    humidity_ratio_from_enthalpy,
    humidity_ratio_from_vapor_pressure,
    moist_air_enthalpy,
    moist_air_specific_volume,
    saturation_humidity_ratio,
    saturation_temperature_from_enthalpy,
    saturation_vapor_pressure,
    vapor_pressure_from_relative_humidity,
    wet_bulb_temperature,
)


class TestPsychrometrics(unittest.TestCase):
    """Test cases for psychrometric functions."""

    def test_saturation_vapor_pressure(self):
        """Test saturation vapor pressure over ice and liquid water."""
        pws = saturation_vapor_pressure([-10, 0, 20, 40])
        np.testing.assert_allclose(pws, [259.91, 611.21, 2339.3, 7384.9], rtol=1e-3)

    def test_humidity_ratio(self):
        """Test humidity ratio from relative humidity."""
        pw = vapor_pressure_from_relative_humidity(20, 50)
        self.assertAlmostEqual(float(pw), 1169.4, delta=1)
        w = humidity_ratio_from_vapor_pressure(pw, 101325)
        self.assertAlmostEqual(float(w), 0.007262, delta=1e-5)
        # saturation humidity ratio at 20°C (ideal gas, without enhancement factor)
        self.assertAlmostEqual(float(saturation_humidity_ratio(20)), 0.014697, delta=1e-5)

    def test_enthalpy(self):
        """Test moist air enthalpy and its inverse."""
        h = moist_air_enthalpy(20, 0.007262)
        self.assertAlmostEqual(float(h), 38.55, delta=0.01)
        self.assertAlmostEqual(float(humidity_ratio_from_enthalpy(h, 20)), 0.007262, places=6)

    def test_specific_volume(self):
        """Test moist air specific volume (ASHRAE table 2 at saturation, 20°C: 0.8497)."""
        v = moist_air_specific_volume(20, saturation_humidity_ratio(20), 101325)
        self.assertAlmostEqual(float(v), 0.8497, delta=1e-3)

    def test_saturation_temperature_from_enthalpy(self):
        """Test the saturation temperature is found back from the saturation enthalpy."""
        t = np.array([-20.0, 0.0, 25.0, 40.0])
        h = moist_air_enthalpy(t, saturation_humidity_ratio(t))
        np.testing.assert_allclose(saturation_temperature_from_enthalpy(h), t, atol=1e-6)

    def test_wet_bulb_temperature(self):
        """Test wet bulb temperature."""
        # saturated air: wet bulb equals dry bulb
        self.assertAlmostEqual(
            float(wet_bulb_temperature(25, saturation_humidity_ratio(25))), 25, places=6
        )
        # 20°C, 50% RH
        w = humidity_ratio_from_vapor_pressure(vapor_pressure_from_relative_humidity(20, 50))
        self.assertAlmostEqual(float(wet_bulb_temperature(20, w)), 13.8, delta=0.1)
        # below freezing, vectorized
        wb = wet_bulb_temperature([-5.0, 30.0], [0.001, 0.01])
        self.assertEqual(wb.shape, (2,))
        self.assertTrue(np.all(wb < [-5.0, 30.0]))


if __name__ == "__main__":
    unittest.main()
