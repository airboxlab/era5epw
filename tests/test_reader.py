"""Tests for the EPW reader module."""

import os
import tempfile
import unittest

import pandas as pd

from era5epw.reader import read_epw_file


class TestEPWReader(unittest.TestCase):
    """Test cases for EPW reader functions."""

    @classmethod
    def setUpClass(cls):
        """Create a test EPW file for all tests."""
        cls.test_epw_file = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".epw")
        cls.test_epw_path = cls.test_epw_file.name

        # Write minimal EPW header and data
        cls.test_epw_file.write("LOCATION,Test City,,,ERA5,n/a,48.86,2.35,1,35\n")
        cls.test_epw_file.write("DESIGN CONDITIONS,0\n")
        cls.test_epw_file.write("TYPICAL/EXTREME PERIODS,0\n")
        cls.test_epw_file.write("GROUND TEMPERATURES,0\n")
        cls.test_epw_file.write("HOLIDAYS/DAYLIGHT SAVINGS,No,0,0,0\n")
        cls.test_epw_file.write("COMMENTS 1,Test data\n")
        cls.test_epw_file.write("COMMENTS 2,Test data\n")
        cls.test_epw_file.write("DATA PERIODS,1,1,Data,Monday,1/1,1/2\n")

        # Write 48 hours of data (2 days)
        for day in range(1, 3):
            for hour in range(1, 25):
                temp = 10.0 + (hour % 12)
                wind = 2.0 + (hour % 6)
                cls.test_epw_file.write(
                    f"2024,1,{day},{hour},0,9,{temp},{temp - 2},80,101325,"
                    f"9999,9999,9999,100,50,40,11000,5250,4760,9999,"
                    f"180,{wind},5,5,9999,77777,0,999999999,999,999,0,99,0.5,0,1\n"
                )
        cls.test_epw_file.close()

    @classmethod
    def tearDownClass(cls):
        """Clean up test EPW file."""
        if os.path.exists(cls.test_epw_path):
            os.remove(cls.test_epw_path)

    def test_read_epw_file_returns_dataframe(self):
        """Test that read_epw_file returns a DataFrame."""
        df = read_epw_file(self.test_epw_path)
        self.assertIsInstance(df, pd.DataFrame)

    def test_read_epw_file_row_count(self):
        """Test that the DataFrame has the expected number of rows."""
        df = read_epw_file(self.test_epw_path)
        self.assertEqual(len(df), 48)

    def test_read_epw_file_datetime_index(self):
        """Test that the DataFrame has a DatetimeIndex."""
        df = read_epw_file(self.test_epw_path)
        self.assertIsInstance(df.index, pd.DatetimeIndex)

    def test_read_epw_file_columns(self):
        """Test that the DataFrame has the expected weather data columns."""
        df = read_epw_file(self.test_epw_path)
        self.assertIn("Dry Bulb Temperature", df.columns)
        self.assertIn("Wind Speed", df.columns)
        self.assertIn("Relative Humidity", df.columns)
        self.assertIn("Atmospheric Station Pressure", df.columns)

    def test_read_epw_file_numeric_values(self):
        """Test that numeric columns contain proper numeric values."""
        df = read_epw_file(self.test_epw_path)
        self.assertTrue(pd.api.types.is_numeric_dtype(df["Dry Bulb Temperature"]))
        self.assertTrue(pd.api.types.is_numeric_dtype(df["Wind Speed"]))

    def test_read_epw_file_usable_for_analysis(self):
        """Test that the returned DataFrame can be used for typical data analysis."""
        df = read_epw_file(self.test_epw_path)

        # Should be able to compute statistics
        stats = df["Dry Bulb Temperature"].describe()
        self.assertIn("mean", stats.index)
        self.assertIn("std", stats.index)

        # Should be able to filter by date
        filtered = df[df.index.day == 1]
        self.assertGreater(len(filtered), 0)


if __name__ == "__main__":
    unittest.main()
