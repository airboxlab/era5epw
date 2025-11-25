import unittest

from era5epw.ads import make_cams_solar_radiation_request
from era5epw.utils import now_utc


class TestADS(unittest.TestCase):
    def test_make_cams_solar_radiation_request(self):
        request = make_cams_solar_radiation_request(
            longitude=10.0,
            latitude=50.0,
            year=2021,
            sky_type="observed_cloud",
            altitude=["0"],
            time_step="1hour",
            time_reference="universal_time",
        )

        self.assertEqual(request["sky_type"], "observed_cloud")
        self.assertEqual(request["location"]["longitude"], 10.0)
        self.assertEqual(request["location"]["latitude"], 50.0)
        self.assertEqual(request["altitude"], ["0"])
        self.assertEqual(request["date"], ["2020-12-31/2021-12-31"])
        self.assertEqual(request["time_step"], "1hour")
        self.assertEqual(request["time_reference"], "universal_time")
        self.assertEqual(request["format"], "netcdf")

    def test_make_cams_solar_radiation_request_current_year(self):
        now = now_utc()
        request = make_cams_solar_radiation_request(
            longitude=10.0,
            latitude=50.0,
            year=now.year,
            sky_type="observed_cloud",
            altitude=["0"],
            time_step="1hour",
            time_reference="universal_time",
        )

        self.assertEqual(
            request["date"], [f"{now.year - 1}-12-31/{now.year}-{now.month:02d}-{now.day:02d}"]
        )

    def test_make_cams_solar_radiation_request_future_year(self):
        now = now_utc()
        request = make_cams_solar_radiation_request(
            longitude=10.0,
            latitude=50.0,
            year=now.year + 1,
            sky_type="observed_cloud",
            altitude=["0"],
            time_step="1hour",
            time_reference="universal_time",
        )

        self.assertIsNone(request, "Request should be None for future years.")
