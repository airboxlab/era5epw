import unittest

from era5epw.cds import make_cds_request, make_intermediate_file_names
from era5epw.utils import now_utc


class TestCDS(unittest.TestCase):
    def test_make_cds_request_era5_single_levels(self):
        requests = make_cds_request(
            ds="reanalysis-era5-single-levels",
            variables=["2m_temperature", "10m_u_component_of_wind"],
            year=2021,
            month=1,
            latitude=50.0,
            longitude=10.0,
        )
        self.assertEqual(len(requests), 2)

        prev_day_request = requests[0]
        self.assertEqual(prev_day_request["year"], ["2020"])
        self.assertEqual(prev_day_request["month"], ["12"])
        self.assertEqual(prev_day_request["day"], ["31"])

        main_request = requests[1]
        self.assertEqual(main_request["dataset"], "reanalysis-era5-single-levels")
        self.assertIn("2m_temperature", main_request["variable"])
        self.assertIn("10m_u_component_of_wind", main_request["variable"])
        self.assertEqual(main_request["year"], ["2021"])
        self.assertEqual(main_request["month"], ["01"])
        self.assertEqual(main_request["day"], [f"{d:02d}" for d in list(range(1, 32))])
        self.assertEqual(main_request["area"], [50.0, 10.0, 50.0, 10.0])

    def test_make_cds_request_era5_single_levels_current_month(self):
        now = now_utc()
        request = make_cds_request(
            ds="reanalysis-era5-single-levels",
            variables=["2m_temperature"],
            year=now.year,
            month=now.month,
            latitude=50.0,
            longitude=10.0,
        )[0]
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

    def test_make_cds_request_era5_timeseries_jan(self):
        requests = make_cds_request(
            ds="reanalysis-era5-single-levels-timeseries",
            variables=["2m_temperature", "10m_u_component_of_wind"],
            year=2021,
            month=1,
            latitude=50.0,
            longitude=10.0,
        )
        self.assertEqual(len(requests), 2)

        prev_day_request = requests[0]
        self.assertEqual(prev_day_request["dataset"], "reanalysis-era5-single-levels-timeseries")
        self.assertIn("2m_temperature", prev_day_request["variable"])
        self.assertIn("10m_u_component_of_wind", prev_day_request["variable"])
        self.assertEqual(prev_day_request["date"], ["2020-12-31/2020-12-31"])
        self.assertEqual(prev_day_request["location"], {"latitude": 50.0, "longitude": 10.0})

        main_request = requests[1]
        self.assertEqual(main_request["date"], ["2021-01-01/2021-01-31"])

    def test_make_cds_request_era5_timeseries_full_year(self):
        prev_day_request = make_cds_request(
            ds="reanalysis-era5-single-levels-timeseries",
            variables=["2m_temperature", "10m_u_component_of_wind"],
            year=2021,
            month=None,
            latitude=50.0,
            longitude=10.0,
        )[0]
        self.assertEqual(prev_day_request["date"], ["2020-12-31/2020-12-31"])

        now = now_utc()
        requests = make_cds_request(
            ds="reanalysis-era5-single-levels-timeseries",
            variables=["2m_temperature", "10m_u_component_of_wind"],
            year=now.year,
            month=None,
            latitude=50.0,
            longitude=10.0,
        )
        prev_day_request = requests[0]
        main_request = requests[1]
        self.assertEqual(prev_day_request["date"], [f"{now.year -1}-12-31/{now.year -1}-12-31"])
        self.assertEqual(
            main_request["date"], [f"{now.year}-01-01/{now.year}-{now.month:02d}-{now.day:02d}"]
        )

    def test_make_cds_request_single_level_with_time_zone(self):
        requests = make_cds_request(
            ds="reanalysis-era5-single-levels",
            variables=["2m_temperature", "10m_u_component_of_wind"],
            year=2021,
            month=1,
            latitude=50.0,
            longitude=10.0,
            time_zone=-8,
        )
        self.assertEqual(len(requests), 1)

        requests = make_cds_request(
            ds="reanalysis-era5-single-levels",
            variables=["2m_temperature", "10m_u_component_of_wind"],
            year=2021,
            month=12,
            latitude=50.0,
            longitude=10.0,
            time_zone=-8,
        )
        self.assertEqual(len(requests), 2)
        main_req = requests[0]
        self.assertEqual(main_req["year"], ["2021"])
        self.assertEqual(main_req["month"], ["12"])
        self.assertEqual(main_req["day"], [f"{d:02d}" for d in list(range(1, 32))])
        tz_req = requests[1]
        self.assertEqual(tz_req["year"], ["2022"])
        self.assertEqual(tz_req["month"], ["01"])
        self.assertEqual(tz_req["day"], ["01"])

        requests = make_cds_request(
            ds="reanalysis-era5-single-levels",
            variables=["2m_temperature", "10m_u_component_of_wind"],
            year=2021,
            month=12,
            latitude=50.0,
            longitude=10.0,
            time_zone=8,
        )
        self.assertEqual(len(requests), 1)

        requests = make_cds_request(
            ds="reanalysis-era5-single-levels",
            variables=["2m_temperature", "10m_u_component_of_wind"],
            year=2021,
            month=1,
            latitude=50.0,
            longitude=10.0,
            time_zone=8,
        )
        self.assertEqual(len(requests), 2)
        main_req = requests[0]
        self.assertEqual(main_req["year"], ["2021"])
        self.assertEqual(main_req["month"], ["01"])
        self.assertEqual(main_req["day"], [f"{d:02d}" for d in list(range(1, 32))])
        tz_req = requests[1]
        self.assertEqual(tz_req["year"], ["2020"])
        self.assertEqual(tz_req["month"], ["12"])
        self.assertEqual(tz_req["day"], ["31"])

    def test_make_cds_request_ts_with_time_zone(self):
        requests = make_cds_request(
            ds="reanalysis-era5-single-levels-timeseries",
            variables=["2m_temperature", "10m_u_component_of_wind"],
            year=2021,
            month=None,
            latitude=50.0,
            longitude=10.0,
            time_zone=-8,
        )
        self.assertEqual(len(requests), 2)
        self.assertEqual(requests[0]["date"], ["2021-01-01/2021-12-31"])
        self.assertEqual(requests[1]["date"], ["2022-01-01/2022-01-01"])

        requests = make_cds_request(
            ds="reanalysis-era5-single-levels-timeseries",
            variables=["2m_temperature", "10m_u_component_of_wind"],
            year=2021,
            month=None,
            latitude=50.0,
            longitude=10.0,
            time_zone=8,
        )
        self.assertEqual(len(requests), 2)
        self.assertEqual(requests[0]["date"], ["2021-01-01/2021-12-31"])
        self.assertEqual(requests[1]["date"], ["2020-12-31/2020-12-31"])

    def test_make_intermediary_file_names_full_year(self):
        tmpdir = "/tmp"
        cds_requests = [
            {
                "variable": ["2m_temperature", "10m_u_component_of_wind"],
                "dataset": "reanalysis-era5-single-levels-timeseries",
                "date": ["2021-01-01/2021-12-31"],
                "location": {"longitude": 10.0, "latitude": 50.0},
            }
        ]
        file_names = make_intermediate_file_names(tmpdir, cds_requests)
        self.assertEqual(len(file_names), 24)
        i = 0
        for month in range(1, 13):
            for var in ["2m_temperature", "10m_u_component_of_wind"]:
                self.assertEqual(
                    file_names[i],
                    f"{tmpdir}/era5_2021_{month:02d}_{var}.nc",
                )
                i += 1

    def test_make_intermediary_file_names_partial_year(self):
        tmpdir = "/tmp"
        year = now_utc().year
        cds_requests = [
            {
                "variable": ["2m_temperature", "10m_u_component_of_wind"],
                "dataset": "reanalysis-era5-single-levels-timeseries",
                "date": [f"{year}-01-01/{year}-07-12"],
            },
            *[
                {
                    "variable": ["total_cloud_cover"],
                    "dataset": "reanalysis-era5-single-levels",
                    "year": [year],
                    "month": [month],
                }
                for month in range(1, 8)
            ],
        ]
        file_names = make_intermediate_file_names(tmpdir, cds_requests)
        self.assertEqual(len(file_names), 21)
        i = 0
        for month in range(1, 8):
            for var in ["2m_temperature", "10m_u_component_of_wind", "total_cloud_cover"]:
                self.assertEqual(
                    file_names[i],
                    f"{tmpdir}/era5_{year}_{month:02d}_{var}.nc",
                )
                i += 1
