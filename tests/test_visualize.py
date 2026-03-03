"""Tests for the EPW visualization module."""

import os
import tempfile
import unittest

import pandas as pd

from era5epw.visualize import (
    create_2d_plot,
    create_3d_plot,
    create_radar_plot,
    get_visible_series,
    read_epw_file,
    visualize_epw,
)


class TestEPWVisualization(unittest.TestCase):
    """Test cases for EPW visualization functions."""

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
                temp = 10.0 + (hour % 12)  # Temperature varies with hour
                wind = 2.0 + (hour % 6)  # Wind speed varies
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

    def test_read_epw_file(self):
        """Test reading an EPW file."""
        df = read_epw_file(self.test_epw_path)

        # Check that we have a DataFrame
        self.assertIsInstance(df, pd.DataFrame)

        # Check that we have the expected number of rows (48 hours)
        self.assertEqual(len(df), 48)

        # Check that the index is a DatetimeIndex
        self.assertIsInstance(df.index, pd.DatetimeIndex)

        # Check that we have the expected columns
        self.assertIn("Dry Bulb Temperature", df.columns)
        self.assertIn("Wind Speed", df.columns)

    def test_get_visible_series(self):
        """Test getting visible series names."""
        df = read_epw_file(self.test_epw_path)
        visible = get_visible_series(df)

        # Check that we have a list
        self.assertIsInstance(visible, list)

        # Check that hidden series are not included
        self.assertNotIn("Year", visible)
        self.assertNotIn("Month", visible)
        self.assertNotIn("Hour", visible)

        # Check that visible series are included
        self.assertIn("Dry Bulb Temperature", visible)
        self.assertIn("Wind Speed", visible)

    def test_create_2d_plot(self):
        """Test creating a 2D plot."""
        df = read_epw_file(self.test_epw_path)
        fig = create_2d_plot(df, "Dry Bulb Temperature")

        # Check that we get a Figure object
        self.assertIsNotNone(fig)

        # Check that the figure has data
        self.assertTrue(len(fig.data) > 0)

        # Check that the figure has a title
        self.assertIn("Dry Bulb Temperature", fig.layout.title.text)

    def test_create_3d_plot(self):
        """Test creating a 3D plot."""
        df = read_epw_file(self.test_epw_path)
        fig = create_3d_plot(df, "Dry Bulb Temperature")

        # Check that we get a Figure object
        self.assertIsNotNone(fig)

        # Check that the figure has data
        self.assertTrue(len(fig.data) > 0)

        # Check that it's a surface plot
        self.assertEqual(fig.data[0].type, "surface")

    def test_create_radar_plot(self):
        """Test creating a radar plot."""
        df = read_epw_file(self.test_epw_path)
        fig = create_radar_plot(df, "Dry Bulb Temperature")

        # Check that we get a Figure object
        self.assertIsNotNone(fig)

        # Check that the figure has data
        self.assertTrue(len(fig.data) > 0)

        # Check that it's a polar plot
        self.assertEqual(fig.data[0].type, "scatterpolargl")

    def test_visualize_epw_2d(self):
        """Test the main visualize_epw function with 2D plot."""
        fig = visualize_epw(self.test_epw_path, plot_type="2D", show=False)
        self.assertIsNotNone(fig)
        self.assertTrue(len(fig.data) > 0)

    def test_visualize_epw_3d(self):
        """Test the main visualize_epw function with 3D plot."""
        fig = visualize_epw(self.test_epw_path, plot_type="3D", show=False)
        self.assertIsNotNone(fig)
        self.assertTrue(len(fig.data) > 0)

    def test_visualize_epw_radar(self):
        """Test the main visualize_epw function with radar plot."""
        fig = visualize_epw(self.test_epw_path, plot_type="radar", show=False)
        self.assertIsNotNone(fig)
        self.assertTrue(len(fig.data) > 0)

    def test_visualize_epw_invalid_series(self):
        """Test that invalid series name raises ValueError."""
        with self.assertRaises(ValueError):
            visualize_epw(self.test_epw_path, series_name="Invalid Series", show=False)

    def test_visualize_epw_invalid_plot_type(self):
        """Test that invalid plot type raises ValueError."""
        with self.assertRaises(ValueError):
            visualize_epw(self.test_epw_path, plot_type="invalid", show=False)  # type: ignore

    def test_html_output(self):
        """Test saving visualization to HTML file."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".html") as f:
            output_path = f.name

        try:
            fig = visualize_epw(self.test_epw_path, plot_type="2D", show=False)
            fig.write_html(output_path)

            # Check that the file was created
            self.assertTrue(os.path.exists(output_path))

            # Check that the file has content
            self.assertGreater(os.path.getsize(output_path), 0)

        finally:
            if os.path.exists(output_path):
                os.remove(output_path)

    def test_different_series(self):
        """Test visualization with different weather series."""
        test_series = ["Wind Speed", "Relative Humidity", "Global Horizontal Radiation"]

        for series in test_series:
            with self.subTest(series=series):
                fig = visualize_epw(self.test_epw_path, series_name=series, show=False)
                self.assertIsNotNone(fig)
                self.assertTrue(len(fig.data) > 0)


if __name__ == "__main__":
    unittest.main()
