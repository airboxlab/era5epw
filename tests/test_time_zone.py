import unittest

from era5epw.ads import make_cams_solar_radiation_request
from era5epw.cds import make_cds_request


class TestTimeZoneHandling(unittest.TestCase):
    def test_make_cds_request_with_positive_time_zone(self):
        """Test that positive time zone adds a day at the end."""
        request = make_cds_request(
            ds="reanalysis-era5-single-levels-timeseries",
            variables=["2m_temperature"],
            year=2021,
            month=None,
            latitude=50.0,
            longitude=10.0,
            time_zone=5,  # +5 hours from UTC
        )
        self.assertEqual(2, len(request))
        self.assertEqual(request[0]["dataset"], "reanalysis-era5-single-levels-timeseries")
        # main request
        self.assertEqual(request[0]["date"], ["2021-01-01/2021-12-31"])
        # time zone adjustment request
        self.assertEqual(request[1]["dataset"], "reanalysis-era5-single-levels-timeseries")
        self.assertEqual(request[1]["date"], ["2020-12-31/2020-12-31"])

    def test_make_cds_request_with_negative_time_zone(self):
        """Test that negative time zone adds a day at the beginning."""
        request = make_cds_request(
            ds="reanalysis-era5-single-levels-timeseries",
            variables=["2m_temperature"],
            year=2021,
            month=None,
            latitude=50.0,
            longitude=10.0,
            time_zone=-5,  # -5 hours from UTC
        )
        self.assertEqual(2, len(request))
        # main request
        self.assertEqual(request[0]["dataset"], "reanalysis-era5-single-levels-timeseries")
        self.assertEqual(request[0]["date"], ["2021-01-01/2021-12-31"])
        # time zone adjustment request
        self.assertEqual(request[1]["dataset"], "reanalysis-era5-single-levels-timeseries")
        self.assertEqual(request[1]["date"], ["2022-01-01/2022-01-01"])

    def test_make_cds_request_without_time_zone(self):
        """Test that without time zone, the date range is unchanged."""
        request = make_cds_request(
            ds="reanalysis-era5-single-levels-timeseries",
            variables=["2m_temperature"],
            year=2021,
            month=None,
            latitude=50.0,
            longitude=10.0,
            time_zone=None,
        )
        self.assertEqual(1, len(request))
        self.assertEqual(request[0]["dataset"], "reanalysis-era5-single-levels-timeseries")
        self.assertEqual(request[0]["date"], ["2021-01-01/2021-12-31"])

    def test_make_cams_request_with_positive_time_zone(self):
        """Test that positive time zone adds a day at the end for CAMS."""
        request = make_cams_solar_radiation_request(
            longitude=10.0,
            latitude=50.0,
            year=2021,
            time_zone=3,  # +3 hours from UTC
        )

        self.assertEqual(request["date"], ["2020-12-31/2021-12-31"])

    def test_make_cams_request_with_negative_time_zone(self):
        """Test that negative time zone adds a day at the beginning for CAMS."""
        request = make_cams_solar_radiation_request(
            longitude=10.0,
            latitude=50.0,
            year=2021,
            time_zone=-8,  # -8 hours from UTC
        )

        self.assertEqual(request["date"], ["2021-01-01/2022-01-01"])

    def test_make_cams_request_without_time_zone(self):
        """Test that without time zone, the date range is unchanged for CAMS."""
        request = make_cams_solar_radiation_request(
            longitude=10.0,
            latitude=50.0,
            year=2021,
            time_zone=None,
        )

        self.assertEqual(request["date"], ["2021-01-01/2021-12-31"])

    def test_make_cams_request_with_zero_time_zone(self):
        """Test that zero time zone doesn't add extra days."""
        request = make_cams_solar_radiation_request(
            longitude=10.0,
            latitude=50.0,
            year=2021,
            time_zone=0,  # UTC
        )

        self.assertEqual(request["date"], ["2021-01-01/2021-12-31"])

    def test_make_cds_request_with_zero_time_zone(self):
        """Test that zero time zone doesn't add extra days."""
        request = make_cds_request(
            ds="reanalysis-era5-single-levels-timeseries",
            variables=["2m_temperature"],
            year=2021,
            month=None,
            latitude=50.0,
            longitude=10.0,
            time_zone=0,  # UTC
        )

        self.assertEqual(1, len(request))
        self.assertEqual(request[0]["date"], ["2021-01-01/2021-12-31"])
