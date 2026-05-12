import unittest

from era5epw.edh import (
    CDS_TO_EDH_VARS,
    _normalize_longitude_input,
    _normalize_longitude_output,
)


class TestEDH(unittest.TestCase):
    def test_normalize_longitude_input_positive(self):
        """Positive longitude should remain unchanged."""
        self.assertAlmostEqual(_normalize_longitude_input(2.5), 2.5)

    def test_normalize_longitude_input_zero(self):
        """Zero longitude should remain unchanged."""
        self.assertAlmostEqual(_normalize_longitude_input(0.0), 0.0)

    def test_normalize_longitude_input_negative(self):
        """Negative longitude should be converted to [0, 360] range."""
        # Nantes: -1.5533 -> 360 - 1.5533 = 358.4467
        self.assertAlmostEqual(_normalize_longitude_input(-1.5533), 358.4467)
        # -180 -> 180
        self.assertAlmostEqual(_normalize_longitude_input(-180.0), 180.0)

    def test_normalize_longitude_output_above_180(self):
        """Longitude above 180 should be converted to negative."""
        self.assertAlmostEqual(_normalize_longitude_output(358.4467), -1.5533)
        self.assertAlmostEqual(_normalize_longitude_output(270.0), -90.0)

    def test_normalize_longitude_output_below_180(self):
        """Longitude below 180 should remain unchanged."""
        self.assertAlmostEqual(_normalize_longitude_output(2.5), 2.5)
        self.assertAlmostEqual(_normalize_longitude_output(0.0), 0.0)
        self.assertAlmostEqual(_normalize_longitude_output(180.0), 180.0)

    def test_cds_to_edh_vars_mapping(self):
        """All expected CDS variables should have EDH mappings."""
        expected_cds_vars = [
            "2m_temperature",
            "2m_dewpoint_temperature",
            "surface_pressure",
            "10m_u_component_of_wind",
            "10m_v_component_of_wind",
            "total_cloud_cover",
            "uv_visible_albedo_for_direct_radiation",
            "snow_depth",
            "soil_temperature_level_1",
            "total_precipitation",
        ]
        for var in expected_cds_vars:
            self.assertIn(var, CDS_TO_EDH_VARS, f"Missing EDH mapping for CDS variable '{var}'")

    def test_cds_to_edh_vars_values(self):
        """EDH short names should match expected values."""
        self.assertEqual(CDS_TO_EDH_VARS["2m_temperature"], "t2m")
        self.assertEqual(CDS_TO_EDH_VARS["2m_dewpoint_temperature"], "d2m")
        self.assertEqual(CDS_TO_EDH_VARS["surface_pressure"], "sp")
        self.assertEqual(CDS_TO_EDH_VARS["10m_u_component_of_wind"], "u10")
        self.assertEqual(CDS_TO_EDH_VARS["10m_v_component_of_wind"], "v10")
        self.assertEqual(CDS_TO_EDH_VARS["total_cloud_cover"], "tcc")
        self.assertEqual(CDS_TO_EDH_VARS["uv_visible_albedo_for_direct_radiation"], "aluvd")
        self.assertEqual(CDS_TO_EDH_VARS["snow_depth"], "sd")
        self.assertEqual(CDS_TO_EDH_VARS["soil_temperature_level_1"], "stl1")
        self.assertEqual(CDS_TO_EDH_VARS["total_precipitation"], "tp")


class TestEDHTokenLoading(unittest.TestCase):
    def test_load_edh_token_missing(self):
        """Should raise FileNotFoundError when no token is available."""
        import os

        # Reset the cached token
        import era5epw.edh
        from era5epw.edh import load_edh_token

        era5epw.edh._edh_token = None
        # Remove env var if set
        old_env = os.environ.pop("EDH_TOKEN", None)
        try:
            with self.assertRaises(FileNotFoundError):
                load_edh_token()
        finally:
            era5epw.edh._edh_token = None
            if old_env is not None:
                os.environ["EDH_TOKEN"] = old_env

    def test_load_edh_token_from_env(self):
        """Should load token from EDH_TOKEN environment variable."""
        import os

        import era5epw.edh

        era5epw.edh._edh_token = None
        os.environ["EDH_TOKEN"] = "test_token_123"
        try:
            token = era5epw.edh.load_edh_token()
            self.assertEqual(token, "test_token_123")
        finally:
            era5epw.edh._edh_token = None
            del os.environ["EDH_TOKEN"]
