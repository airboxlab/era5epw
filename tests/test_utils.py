import unittest

from era5epw.utils import make_cds_days_list, now_utc


class TestUtils(unittest.TestCase):
    def test_make_cds_days_list(self):
        now = now_utc()

        self.assertEqual(make_cds_days_list(2021, 1), [f"{i:02d}" for i in range(1, 32)])
        self.assertEqual(make_cds_days_list(2020, 2), [f"{i:02d}" for i in range(1, 30)])
        self.assertEqual(make_cds_days_list(2021, 2), [f"{i:02d}" for i in range(1, 29)])
        self.assertEqual(make_cds_days_list(2021, 4), [f"{i:02d}" for i in range(1, 31)])

        current_year = now.year
        current_month = now.month
        self.assertEqual(
            make_cds_days_list(current_year, current_month),
            [f"{i:02d}" for i in range(1, now.day + 1)],
        )
        next_year = current_year + 1
        self.assertEqual(make_cds_days_list(next_year, 1), [])
