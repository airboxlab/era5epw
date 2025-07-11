import unittest

from era5epw.cds import make_cds_request
from era5epw.utils import now_utc


class TestCDS(unittest.TestCase):
    def test_make_cds_request_era5_single_levels(self):
        request = make_cds_request(
            ds="reanalysis-era5-single-levels",
            variables=["2m_temperature", "10m_u_component_of_wind"],
            year=2021,
            month=1,
            latitude=50.0,
            longitude=10.0,
        )

        self.assertEqual(request["dataset"], "reanalysis-era5-single-levels")
        self.assertIn("2m_temperature", request["variable"])
        self.assertIn("10m_u_component_of_wind", request["variable"])
        self.assertEqual(request["year"], ["2021"])
        self.assertEqual(request["month"], ["01"])
        self.assertEqual(request["day"], [f"{d:02d}" for d in list(range(1, 32))])
        self.assertEqual(request["area"], [50.0, 10.0, 50.0, 10.0])

    def test_make_cds_request_era5_single_levels_current_month(self):
        now = now_utc()
        request = make_cds_request(
            ds="reanalysis-era5-single-levels",
            variables=["2m_temperature"],
            year=now.year,
            month=now.month,
            latitude=50.0,
            longitude=10.0,
        )
        self.assertEqual(request["year"], [str(now.year)])
        self.assertEqual(request["month"], [f"{now.month:02d}"])
        self.assertEqual(request["day"], [f"{d:02d}" for d in range(1, now.day + 1)])

    def test_make_cds_request_future_date(self):
        now = now_utc()
        request = make_cds_request(
            ds="reanalysis-era5-single-levels",
            variables=["2m_temperature"],
            year=now.year,
            month=now.month + 1,
            latitude=50.0,
            longitude=10.0,
        )
        self.assertIsNone(request, "Request should be None for future dates.")
        request = make_cds_request(
            ds="reanalysis-era5-single-levels",
            variables=["2m_temperature"],
            year=now.year + 1,
            month=1,
            latitude=50.0,
            longitude=10.0,
        )
        self.assertIsNone(request, "Request should be None for future dates.")

    def test_make_cds_request_era5_timeseries(self):
        request = make_cds_request(
            ds="reanalysis-era5-single-levels-timeseries",
            variables=["2m_temperature", "10m_u_component_of_wind"],
            year=2021,
            month=1,
            latitude=50.0,
            longitude=10.0,
        )

        self.assertEqual(request["dataset"], "reanalysis-era5-single-levels-timeseries")
        self.assertIn("2m_temperature", request["variable"])
        self.assertIn("10m_u_component_of_wind", request["variable"])
        self.assertEqual(request["date"], ["2021-01-01/2021-01-31"])
        self.assertEqual(request["location"], {"latitude": 50.0, "longitude": 10.0})

    def test_make_cds_request_era5_timeseries_full_year(self):
        request = make_cds_request(
            ds="reanalysis-era5-single-levels-timeseries",
            variables=["2m_temperature", "10m_u_component_of_wind"],
            year=2021,
            month=None,
            latitude=50.0,
            longitude=10.0,
        )
        self.assertEqual(request["date"], ["2021-01-01/2021-12-31"])

        now = now_utc()
        request = make_cds_request(
            ds="reanalysis-era5-single-levels-timeseries",
            variables=["2m_temperature", "10m_u_component_of_wind"],
            year=now.year,
            month=None,
            latitude=50.0,
            longitude=10.0,
        )
        self.assertEqual(
            request["date"], [f"{now.year}-01-01/{now.year}-{now.month:02d}-{now.day:02d}"]
        )
