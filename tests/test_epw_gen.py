import unittest

import numpy as np
import pandas as pd

from era5epw.main import (
    calc_monthly_soil_temperature,
    calc_rh,
    get_first_weekday_of_year,
    make_data_period_end_date,
)


class TestEpwGeneration(unittest.TestCase):
    def test_monthly_soil_temperature(self):
        # Create a sample DataFrame with soil temperature data
        dates = pd.date_range(start="2023-01-01", end="2023-12-31", freq="D")
        soil_temp = pd.Series([260 + i % 30 for i in range(len(dates))], index=dates)

        # Compute monthly average soil temperature
        monthly_avg = calc_monthly_soil_temperature(soil_temp)

        # Check the result
        self.assertEqual(len(monthly_avg), 12)
        self.assertTrue((monthly_avg >= 0).all())
        self.assertTrue((monthly_avg <= 10).all())
        print(",".join(monthly_avg.round(1).astype(str).tolist()))

    def test_calc_rh(self):
        # Sample dry bulb and dew point temperatures
        dry_bulb_temp = np.array([20, 25, 30])
        dew_point_temp = np.array([10, 15, 20])

        # Calculate relative humidity
        rh = calc_rh(dry_bulb_temp, dew_point_temp)

        # Check the result
        self.assertTrue((rh >= 0).all())
        self.assertTrue((rh <= 100).all())

    def test_first_day_of_year(self):
        self.assertEqual(get_first_weekday_of_year(2023), "Sunday")
        self.assertEqual(get_first_weekday_of_year(2024), "Monday")

    def test_make_data_period_end_date(self):
        df = pd.DataFrame(
            {
                "Month": [1, 1, 1, 2, 2, 3],
                "Day": [1, 2, 3, 1, 2, 3],
            }
        )
        dp_end_date = make_data_period_end_date(df)
        self.assertEqual(dp_end_date, "3/3")
